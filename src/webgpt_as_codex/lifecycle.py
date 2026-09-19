from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

from .discovery import discover_component, process_health, process_snapshot
from .paths import ensure_state_dirs, user_home
from .provision import ApprovedArtifact, provision_artifact
from .registry import Component, load_components
from .stateio import atomic_write_json

_VERSION_RE = re.compile(
    r"(?i)(?:^|[^0-9])v?(\d+(?:\.\d+){1,3}(?:[-+][0-9a-z.-]+)?)"
)
_STABLE_VERSION_RE = re.compile(r"^v?\d+(?:\.\d+){1,3}$", re.IGNORECASE)
_SUPPORTED_STRATEGIES = {
    "uv-tool",
    "npm-global",
    "winget",
    "github-release",
    "manual",
}
_WINGET_TOOLCHAIN = {
    "uv": "astral-sh.uv",
    "npm": "OpenJS.NodeJS.LTS",
}
_LATEST_CACHE_TTL_SECONDS = 24 * 60 * 60


@dataclass(frozen=True)
class LatestRelease:
    component_id: str
    version: str
    source: str
    artifact_name: str | None = None
    download_url: str | None = None
    sha256: str | None = None


@dataclass(frozen=True)
class InstallSpec:
    strategy: str
    package: str | None
    latest: dict[str, Any]
    requirements: tuple[str, ...] = ()
    compatibility: dict[str, str] | None = None
    winget_id: str | None = None
    github_repo: str | None = None
    assets: dict[str, str] | None = None
    archive_member: str | None = None
    destination: str | None = None


def _run(command: list[str], *, timeout: float = 120.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
        shell=False,
    )


def _find_command(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    if os.name != "nt":
        return None
    filename = name if name.lower().endswith((".exe", ".cmd", ".bat")) else f"{name}.exe"
    candidates = [user_home() / ".local" / "bin" / filename]
    local_appdata = os.getenv("LOCALAPPDATA")
    if local_appdata:
        candidates.append(Path(local_appdata) / "Microsoft" / "WinGet" / "Links" / filename)
    if name.lower() in {"node", "npm"}:
        program_files = os.getenv("ProgramFiles", r"C:\Program Files")
        node_name = "npm.cmd" if name.lower() == "npm" else "node.exe"
        candidates.append(Path(program_files) / "nodejs" / node_name)
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None


def toolchain_environment() -> dict[str, Any]:
    tools: dict[str, Any] = {}
    for name, version_args in (
        ("git", ["--version"]),
        ("node", ["--version"]),
        ("npm", ["--version"]),
        ("uv", ["--version"]),
    ):
        path = _find_command(name)
        version = None
        if path:
            try:
                result = _run([path, *version_args], timeout=10)
            except (OSError, subprocess.SubprocessError):
                result = None
            if result is not None and result.returncode == 0:
                version = (result.stdout or result.stderr).strip().splitlines()[0] or None
        tools[name] = {
            "available": bool(path),
            "path": path,
            "version": version,
        }
    winget = shutil.which("winget") if os.name == "nt" else None
    tools["winget"] = {
        "available": bool(winget),
        "path": winget,
        "version": None,
    }
    return tools


def install_spec(component: Component) -> InstallSpec | None:
    raw = component.raw.get("install")
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise TypeError(f"{component.id} install metadata must be an object")
    strategy = raw.get("strategy")
    if strategy not in _SUPPORTED_STRATEGIES:
        raise ValueError(f"{component.id} has unsupported install strategy")
    package = raw.get("package")
    if package is not None and (not isinstance(package, str) or not package.strip()):
        raise ValueError(f"{component.id} install package must be text")
    latest = raw.get("latest")
    if not isinstance(latest, dict) or not isinstance(latest.get("source"), str):
        raise TypeError(f"{component.id} install metadata requires latest.source")
    requirements_raw = raw.get("requirements", [])
    if not isinstance(requirements_raw, list) or not all(
        isinstance(value, str) and value.strip() for value in requirements_raw
    ):
        raise TypeError(f"{component.id} install requirements must be a string list")
    requirements = tuple(dict.fromkeys(value.strip() for value in requirements_raw))
    compatibility_raw = raw.get("compatibility")
    compatibility: dict[str, str] | None
    if compatibility_raw is None:
        compatibility = None
    elif not isinstance(compatibility_raw, dict):
        raise TypeError(f"{component.id} compatibility must be an object")
    else:
        allowed_compatibility = {"min_version", "max_version_exclusive"}
        unknown = sorted(set(compatibility_raw) - allowed_compatibility)
        if unknown:
            raise ValueError(
                f"{component.id} compatibility contains unsupported fields: "
                + ", ".join(unknown)
            )
        compatibility = {}
        for key in sorted(allowed_compatibility):
            value = compatibility_raw.get(key)
            if value is None:
                continue
            if not isinstance(value, str):
                raise TypeError(f"{component.id} {key} must be text")
            compatibility[key] = _stable_version(value)
        if not compatibility:
            raise ValueError(f"{component.id} compatibility policy is empty")
    winget_id = raw.get("winget_id")
    github_repo = raw.get("github_repo")
    assets = raw.get("assets")
    archive_member = raw.get("archive_member")
    destination = raw.get("destination")
    if strategy == "uv-tool" and not package:
        raise ValueError(f"{component.id} uv-tool strategy requires package")
    if strategy == "npm-global" and not package:
        raise ValueError(f"{component.id} npm-global strategy requires package")
    if strategy == "winget" and not isinstance(winget_id, str):
        raise ValueError(f"{component.id} winget strategy requires winget_id")
    if strategy == "github-release":
        if not isinstance(github_repo, str) or "/" not in github_repo:
            raise ValueError(f"{component.id} github-release strategy requires github_repo")
        if not isinstance(assets, dict) or not assets:
            raise ValueError(f"{component.id} github-release strategy requires assets")
        if not isinstance(destination, str) or not destination:
            raise ValueError(f"{component.id} github-release strategy requires destination")
        assets = {str(key): str(value) for key, value in assets.items()}
    if strategy != "manual" and compatibility is None:
        raise ValueError(f"{component.id} automatic install requires compatibility policy")
    return InstallSpec(
        strategy=strategy,
        package=package,
        latest=dict(latest),
        requirements=requirements,
        compatibility=compatibility,
        winget_id=winget_id if isinstance(winget_id, str) else None,
        github_repo=github_repo if isinstance(github_repo, str) else None,
        assets=assets if isinstance(assets, dict) else None,
        archive_member=archive_member if isinstance(archive_member, str) else None,
        destination=destination if isinstance(destination, str) else None,
    )


def _request_json(url: str) -> dict[str, Any]:
    response = requests.get(
        url,
        headers={"User-Agent": "WebGPT-as-Codex/0.1"},
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise TypeError("release source returned non-object JSON")
    return data


def _architecture() -> str:
    raw = platform.machine().lower()
    if raw in {"amd64", "x86_64"}:
        return "amd64"
    if raw in {"arm64", "aarch64"}:
        return "arm64"
    raise RuntimeError(f"unsupported Windows architecture: {raw or 'unknown'}")


def _stable_version(value: str) -> str:
    value = value.strip()
    if not _STABLE_VERSION_RE.fullmatch(value):
        raise ValueError(f"release version is not stable semver-like text: {value!r}")
    return value[1:] if value.lower().startswith("v") else value


def _latest_from_pypi(component: Component, spec: InstallSpec) -> LatestRelease:
    package = str(spec.latest.get("package") or spec.package or "")
    if not package:
        raise ValueError("PyPI source requires package")
    data = _request_json(f"https://pypi.org/pypi/{quote(package, safe='')}/json")
    info = data.get("info")
    if not isinstance(info, dict):
        raise TypeError("PyPI response missing info")
    version = _stable_version(str(info.get("version") or ""))
    return LatestRelease(component.id, version, "pypi")


def _latest_from_npm(component: Component, spec: InstallSpec) -> LatestRelease:
    package = str(spec.latest.get("package") or spec.package or "")
    if not package:
        raise ValueError("npm source requires package")
    data = _request_json(
        f"https://registry.npmjs.org/{quote(package, safe='')}/latest"
    )
    version = _stable_version(str(data.get("version") or ""))
    return LatestRelease(component.id, version, "npm")


def _latest_from_github(component: Component, spec: InstallSpec) -> LatestRelease:
    repo = str(spec.latest.get("repo") or spec.github_repo or "")
    if not repo or "/" not in repo:
        raise ValueError("GitHub release source requires repo")
    data = _request_json(f"https://api.github.com/repos/{repo}/releases/latest")
    if data.get("draft") is True or data.get("prerelease") is True:
        raise ValueError("GitHub latest release is not stable")
    version = _stable_version(str(data.get("tag_name") or ""))
    arch = _architecture()
    if not spec.assets or arch not in spec.assets:
        raise ValueError(f"no approved Windows asset mapping for {arch}")
    expected_name = spec.assets[arch]
    assets = data.get("assets")
    if not isinstance(assets, list):
        raise TypeError("GitHub release has no asset list")
    selected = next(
        (
            item
            for item in assets
            if isinstance(item, dict) and item.get("name") == expected_name
        ),
        None,
    )
    if selected is None:
        raise ValueError(f"GitHub release missing expected asset {expected_name}")
    digest = str(selected.get("digest") or "")
    if not digest.startswith("sha256:") or len(digest) != 71:
        raise ValueError("GitHub release asset has no SHA-256 digest")
    url = str(selected.get("browser_download_url") or "")
    expected_prefix = f"https://github.com/{repo}/releases/download/"
    if not url.startswith(expected_prefix):
        raise ValueError("GitHub release asset URL escaped the approved repository")
    return LatestRelease(
        component.id,
        version,
        "github-release",
        artifact_name=expected_name,
        download_url=url,
        sha256=digest.removeprefix("sha256:").lower(),
    )


def _latest_from_winget(component: Component, spec: InstallSpec) -> LatestRelease:
    winget = shutil.which("winget")
    if not winget or not spec.winget_id:
        raise FileNotFoundError("winget is unavailable")
    result = _run(
        [
            winget,
            "show",
            "--id",
            spec.winget_id,
            "--exact",
            "--accept-source-agreements",
            "--disable-interactivity",
        ],
        timeout=45,
    )
    if result.returncode:
        raise RuntimeError("winget show failed")
    for line in result.stdout.splitlines()[:16]:
        match = re.search(r":\s*(\d+(?:\.\d+){1,3})\s*$", line)
        if match:
            return LatestRelease(component.id, _stable_version(match.group(1)), "winget")
    raise ValueError("winget output did not expose a stable package version")


def resolve_latest(component: Component) -> LatestRelease:
    spec = install_spec(component)
    if spec is None:
        raise ValueError(f"{component.id} has no install metadata")
    source = spec.latest["source"]
    if source == "pypi":
        return _latest_from_pypi(component, spec)
    if source == "npm":
        return _latest_from_npm(component, spec)
    if source == "github-release":
        return _latest_from_github(component, spec)
    if source == "winget":
        return _latest_from_winget(component, spec)
    raise ValueError(f"unsupported latest source: {source}")


def _extract_version(text: str) -> str | None:
    match = _VERSION_RE.search(text.strip())
    if not match:
        return None
    value = match.group(1)
    try:
        return _stable_version(value)
    except ValueError:
        return None


def _version_key(value: str) -> tuple[int, ...] | None:
    try:
        stable = _stable_version(value)
    except ValueError:
        return None
    return tuple(int(part) for part in stable.split("."))


def compare_versions(current: str, latest: str) -> int | None:
    left = _version_key(current)
    right = _version_key(latest)
    if left is None or right is None:
        return None
    width = max(len(left), len(right))
    left += (0,) * (width - len(left))
    right += (0,) * (width - len(right))
    return (left > right) - (left < right)


def version_compatible(spec: InstallSpec, version: str) -> tuple[bool | None, str]:
    policy = spec.compatibility
    if policy is None:
        return None, "no-compatibility-policy"
    if _version_key(version) is None:
        return None, "version-unparseable"
    minimum = policy.get("min_version")
    maximum = policy.get("max_version_exclusive")
    if minimum is not None:
        comparison = compare_versions(version, minimum)
        if comparison is None:
            return None, "minimum-incomparable"
        if comparison < 0:
            return False, f"below-minimum:{minimum}"
    if maximum is not None:
        comparison = compare_versions(version, maximum)
        if comparison is None:
            return None, "maximum-incomparable"
        if comparison >= 0:
            return False, f"at-or-above-maximum:{maximum}"
    return True, "within-policy"


def _ownership_path(component_id: str) -> Path:
    return ensure_state_dirs() / "ownership" / "components" / f"{component_id}.json"


def ownership_receipt(component_id: str) -> dict[str, Any] | None:
    path = _ownership_path(component_id)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or data.get("component_id") != component_id:
        return None
    return data


def _write_ownership(component: Component, *, version: str, strategy: str) -> None:
    atomic_write_json(
        _ownership_path(component.id),
        {
            "schema_version": 1,
            "component_id": component.id,
            "version": version,
            "strategy": strategy,
            "installed_by_webgpt": True,
            "runtime_lifecycle_authority": False,
            "installed_at": time.time(),
        },
        sort_keys=True,
    )


def _installed_version_from_command(component: Component) -> str | None:
    command = component.raw.get("version_command")
    if not isinstance(command, list) or not command:
        return None
    executable = _find_command(str(command[0]))
    if not executable:
        machine_binary = component.raw.get("machine_binary")
        if isinstance(machine_binary, str):
            relative = Path(machine_binary)
            if not relative.is_absolute() and ".." not in relative.parts:
                candidate = ensure_state_dirs() / relative
                if candidate.is_file():
                    executable = str(candidate)
    if not executable:
        return None
    try:
        result = _run([executable, *[str(part) for part in command[1:]]], timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode:
        return None
    return _extract_version((result.stdout or "") + "\n" + (result.stderr or ""))


def _installed_npm_version(package: str) -> str | None:
    npm = _find_command("npm")
    if not npm:
        return None
    try:
        result = _run(
            [npm, "list", "-g", package, "--depth=0", "--json"],
            timeout=25,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode not in {0, 1}:
        return None
    try:
        data = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return None
    dependencies = data.get("dependencies")
    if not isinstance(dependencies, dict):
        return None
    item = dependencies.get(package)
    if not isinstance(item, dict):
        return None
    version = item.get("version")
    if not isinstance(version, str):
        return None
    try:
        return _stable_version(version)
    except ValueError:
        return None


def _installed_uv_version(package: str) -> str | None:
    uv = _find_command("uv")
    if not uv:
        return None
    try:
        result = _run([uv, "tool", "list"], timeout=25)
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode:
        return None
    normalized = package.lower().replace("_", "-")
    for line in result.stdout.splitlines():
        match = re.match(r"^\s*([^\s]+)\s+v?(\d+(?:\.\d+){1,3})\b", line)
        if not match:
            continue
        name = match.group(1).lower().replace("_", "-")
        if name == normalized:
            try:
                return _stable_version(match.group(2))
            except ValueError:
                return None
    return None


def installed_version(component: Component, spec: InstallSpec) -> str | None:
    receipt = ownership_receipt(component.id)
    if receipt is not None and isinstance(receipt.get("version"), str):
        return str(receipt["version"])
    if spec.strategy == "npm-global" and spec.package:
        version = _installed_npm_version(spec.package)
        if version:
            return version
    if spec.strategy == "uv-tool" and spec.package:
        version = _installed_uv_version(spec.package)
        if version:
            return version
    if component.id == "tailscale":
        try:
            from .prerequisites import tailscale_environment

            version = tailscale_environment().get("version")
            if isinstance(version, str) and _version_key(version) is not None:
                return _stable_version(version)
        except (OSError, RuntimeError, TypeError, ValueError):
            pass
    return _installed_version_from_command(component)


def _latest_cache_path(component_id: str) -> Path:
    return ensure_state_dirs() / "cache" / "latest" / f"{component_id}.json"


def _write_latest_cache(component: Component, latest: LatestRelease) -> None:
    atomic_write_json(
        _latest_cache_path(component.id),
        {
            "schema_version": 1,
            "component_id": component.id,
            "version": latest.version,
            "source": latest.source,
            "artifact_name": latest.artifact_name,
            "download_url": latest.download_url,
            "sha256": latest.sha256,
            "resolved_at": time.time(),
        },
        sort_keys=True,
    )


def _read_latest_cache(
    component: Component,
    *,
    max_age_seconds: float = _LATEST_CACHE_TTL_SECONDS,
) -> LatestRelease | None:
    path = _latest_cache_path(component.id)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or data.get("component_id") != component.id:
        return None
    try:
        age = time.time() - float(data["resolved_at"])
        version = _stable_version(str(data["version"]))
    except (KeyError, TypeError, ValueError):
        return None
    if age < 0 or age > max_age_seconds:
        return None
    source = data.get("source")
    if not isinstance(source, str):
        return None
    artifact_name = data.get("artifact_name")
    download_url = data.get("download_url")
    digest = data.get("sha256")
    if artifact_name is not None and not isinstance(artifact_name, str):
        return None
    if download_url is not None and not isinstance(download_url, str):
        return None
    if digest is not None and (
        not isinstance(digest, str)
        or not re.fullmatch(r"[0-9a-f]{64}", digest, re.IGNORECASE)
    ):
        return None
    if source == "github-release":
        spec = install_spec(component)
        if (
            spec is None
            or not spec.github_repo
            or not artifact_name
            or not download_url
            or not digest
            or not download_url.startswith(
                f"https://github.com/{spec.github_repo}/releases/download/"
            )
        ):
            return None
    return LatestRelease(
        component.id,
        version,
        source,
        artifact_name=artifact_name,
        download_url=download_url,
        sha256=digest.lower() if isinstance(digest, str) else None,
    )


def _safe_latest(component: Component) -> tuple[LatestRelease | None, str | None]:
    try:
        latest = resolve_latest(component)
        _write_latest_cache(component, latest)
        return latest, None
    except (
        FileNotFoundError,
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
        requests.RequestException,
        subprocess.SubprocessError,
    ) as exc:
        cached = _read_latest_cache(component)
        if cached is not None:
            return cached, f"{type(exc).__name__}:using-verified-cache"
        return None, type(exc).__name__


def plan_component(component: Component) -> dict[str, Any]:
    try:
        spec = install_spec(component)
    except (TypeError, ValueError) as exc:
        return {
            "component_id": component.id,
            "action": "diagnose-invalid-install-metadata",
            "reason": type(exc).__name__,
            "mutation": False,
        }
    if spec is None:
        return {
            "component_id": component.id,
            "action": "diagnose-no-install-metadata",
            "mutation": False,
        }

    discovery = discover_component(component)
    snapshot = process_snapshot()
    process_up = process_health(component, snapshot)
    listener_up = discovery.get("listener_up")
    ownership = ownership_receipt(component.id)
    owned = ownership is not None and ownership.get("installed_by_webgpt") is True
    latest, latest_error = _safe_latest(component)
    latest_fresh = latest is not None and latest_error is None
    latest_provenance = (
        "fresh"
        if latest_fresh
        else "verified-cache"
        if latest is not None and latest_error and "using-verified-cache" in latest_error
        else "unavailable"
    )
    current = installed_version(component, spec)
    comparison = (
        compare_versions(current, latest.version)
        if current is not None and latest is not None
        else None
    )
    installed_compatible, installed_compatibility_reason = (
        version_compatible(spec, current)
        if current is not None
        else (None, "installed-version-unknown")
    )
    latest_compatible, latest_compatibility_reason = (
        version_compatible(spec, latest.version)
        if latest is not None
        else (None, "latest-unavailable")
    )
    requirements_state = toolchain_environment()
    missing_requirements = [
        requirement
        for requirement in spec.requirements
        if not bool(requirements_state.get(requirement, {}).get("available"))
    ]

    common = {
        "component_id": component.id,
        "display_name": component.display_name,
        "strategy": spec.strategy,
        "required": component.required,
        "listener_up": listener_up,
        "process_up": process_up,
        "installed_by_path": discovery.get("installed_by_path"),
        "installed_version": current,
        "latest_version": latest.version if latest else None,
        "latest_source": latest.source if latest else None,
        "latest_error": latest_error,
        "latest_fresh": latest_fresh,
        "latest_provenance": latest_provenance,
        "verified_compatible": installed_compatible,
        "installed_compatibility_reason": installed_compatibility_reason,
        "latest_compatible": latest_compatible,
        "latest_compatibility_reason": latest_compatibility_reason,
        "requirements": list(spec.requirements),
        "missing_requirements": missing_requirements,
        "webgpt_install_owned": owned,
        "runtime_lifecycle_authority": bool(
            ownership and ownership.get("runtime_lifecycle_authority") is True
        ),
        "mutation": False,
    }

    if spec.strategy == "manual":
        return {
            **common,
            "action": "manual-required" if listener_up is not True else "preserve-manual",
        }

    if listener_up is True:
        if discovery.get("protocol_healthy") is False:
            return {**common, "action": "diagnose-listener-conflict", "blocking": True}
        if not latest_fresh:
            return {
                **common,
                "action": "preserve-existing-latest-unavailable",
                "blocking": True,
            }
        if installed_compatible is False:
            return {
                **common,
                "action": "preserve-running-incompatible-diagnose",
                "blocking": True,
            }
        if latest_compatible is False:
            return {
                **common,
                "action": "preserve-current-latest-incompatible",
                "blocking": True,
            }
        if comparison is not None and comparison < 0:
            return {
                **common,
                "action": (
                    "upgrade-owned-requires-stop"
                    if owned
                    else "preserve-external-upgrade-available"
                ),
            }
        return {**common, "action": "preserve-healthy"}

    if component.transport == "system" and process_up is True and listener_up is None:
        if not latest_fresh:
            return {
                **common,
                "action": "preserve-system-latest-unavailable",
                "blocking": True,
            }
        if installed_compatible is False:
            return {
                **common,
                "action": "preserve-running-incompatible-diagnose",
                "blocking": True,
            }
        if latest_compatible is False:
            return {
                **common,
                "action": "preserve-current-latest-incompatible",
                "blocking": True,
            }
        if comparison is not None and comparison < 0:
            return {
                **common,
                "action": (
                    "upgrade-owned-requires-stop"
                    if owned
                    else "preserve-external-upgrade-available"
                ),
            }
        return {**common, "action": "preserve-healthy-system"}

    if process_up is True:
        return {**common, "action": "diagnose-running-unhealthy"}

    present = bool(discovery.get("installed_by_path")) or owned or current is not None
    if present:
        if not latest_fresh:
            return {**common, "action": "diagnose-latest-unavailable", "blocking": True}
        if current is None:
            return {**common, "action": "diagnose-version-unknown", "blocking": True}
        if installed_compatible is False:
            return {
                **common,
                "action": "diagnose-installed-incompatible",
                "blocking": True,
            }
        if latest_compatible is False:
            return {
                **common,
                "action": "preserve-current-latest-incompatible",
                "blocking": True,
            }
        if comparison is None:
            return {**common, "action": "diagnose-version-incomparable", "blocking": True}
        if comparison < 0:
            return {
                **common,
                "action": "upgrade-owned" if owned else "upgrade-external-requires-adoption",
            }
        if comparison > 0:
            return {**common, "action": "preserve-newer"}
        return {**common, "action": "preserve-installed-current"}

    if not latest_fresh:
        return {
            **common,
            "action": "install-blocked-latest-unavailable",
            "blocking": True,
        }
    if latest_compatible is not True:
        return {
            **common,
            "action": "install-blocked-incompatible-latest",
            "blocking": True,
        }
    return {**common, "action": "install-missing"}


def _ensure_winget_tool(tool: str) -> dict[str, Any]:
    path = _find_command(tool)
    if path:
        return {"ok": True, "status": "already-available", "path": path}
    winget = shutil.which("winget")
    package_id = _WINGET_TOOLCHAIN.get(tool)
    if not winget or not package_id:
        return {"ok": False, "status": "toolchain-installer-unavailable", "tool": tool}
    result = _run(
        [
            winget,
            "install",
            "--id",
            package_id,
            "--exact",
            "--silent",
            "--accept-package-agreements",
            "--accept-source-agreements",
            "--disable-interactivity",
        ],
        timeout=240,
    )
    path = _find_command(tool)
    return {
        "ok": result.returncode == 0 and bool(path),
        "status": "installed" if result.returncode == 0 and path else "install-failed",
        "tool": tool,
        "path": path,
    }


def _install_uv(spec: InstallSpec, version: str) -> dict[str, Any]:
    ready = _ensure_winget_tool("uv")
    if not ready["ok"]:
        return ready
    uv = str(ready["path"])
    requirement = f"{spec.package}=={version}"
    result = _run([uv, "tool", "install", "--upgrade", requirement], timeout=300)
    return {
        "ok": result.returncode == 0,
        "status": "installed" if result.returncode == 0 else "install-failed",
    }


def _install_npm(spec: InstallSpec, version: str) -> dict[str, Any]:
    ready = _ensure_winget_tool("npm")
    if not ready["ok"]:
        return ready
    npm = str(ready["path"])
    requirement = f"{spec.package}@{version}"
    result = _run(
        [npm, "install", "-g", requirement, "--no-audit", "--no-fund"],
        timeout=300,
    )
    return {
        "ok": result.returncode == 0,
        "status": "installed" if result.returncode == 0 else "install-failed",
    }


def _install_winget(spec: InstallSpec, *, upgrade: bool = False) -> dict[str, Any]:
    winget = shutil.which("winget")
    if not winget or not spec.winget_id:
        return {"ok": False, "status": "winget-unavailable"}
    verb = "upgrade" if upgrade else "install"
    result = _run(
        [
            winget,
            verb,
            "--id",
            spec.winget_id,
            "--exact",
            "--silent",
            "--accept-package-agreements",
            "--accept-source-agreements",
            "--disable-interactivity",
        ],
        timeout=300,
    )
    return {
        "ok": result.returncode == 0,
        "status": (
            "upgraded"
            if upgrade and result.returncode == 0
            else "installed"
            if result.returncode == 0
            else "install-failed"
        ),
    }


def _install_github(
    component: Component,
    spec: InstallSpec,
    latest: LatestRelease,
    *,
    force: bool = False,
) -> dict[str, Any]:
    if not all((latest.artifact_name, latest.download_url, latest.sha256, spec.destination)):
        return {"ok": False, "status": "release-artifact-incomplete"}
    artifact = ApprovedArtifact(
        component_id=component.id,
        version=latest.version,
        architecture=_architecture(),
        source_url=str(latest.download_url),
        sha256=str(latest.sha256),
        destination=str(spec.destination),
        archive_member=spec.archive_member,
    )
    return provision_artifact(artifact, force=force)


def apply_component(
    component: Component,
    *,
    adopt_external: bool = False,
) -> dict[str, Any]:
    plan = plan_component(component)
    action = plan["action"]
    allowed = {"install-missing", "upgrade-owned"}
    if adopt_external:
        allowed.add("upgrade-external-requires-adoption")
    if action not in allowed:
        return {**plan, "applied": False}

    spec = install_spec(component)
    if spec is None:
        return {**plan, "applied": False, "status": "install-metadata-missing"}
    latest, latest_error = _safe_latest(component)
    if latest is None or latest_error is not None:
        return {
            **plan,
            "applied": False,
            "ok": False,
            "status": "latest-resolution-failed",
            "latest_error": latest_error,
            "latest_fresh": False,
        }
    latest_compatible, compatibility_reason = version_compatible(spec, latest.version)
    if latest_compatible is not True:
        return {
            **plan,
            "applied": False,
            "ok": False,
            "status": "latest-incompatible",
            "latest_compatible": latest_compatible,
            "latest_compatibility_reason": compatibility_reason,
        }

    try:
        if spec.strategy == "uv-tool":
            result = _install_uv(spec, latest.version)
        elif spec.strategy == "npm-global":
            result = _install_npm(spec, latest.version)
        elif spec.strategy == "winget":
            result = _install_winget(spec, upgrade=action != "install-missing")
        elif spec.strategy == "github-release":
            result = _install_github(
                component,
                spec,
                latest,
                force=action != "install-missing",
            )
        else:
            return {**plan, "applied": False, "status": "manual-required"}
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        return {
            **plan,
            "applied": False,
            "status": "install-failed",
            "failure_type": type(exc).__name__,
        }

    if not result.get("ok"):
        return {**plan, "applied": False, **result}

    _write_ownership(component, version=latest.version, strategy=spec.strategy)
    return {
        **plan,
        "applied": True,
        "ok": True,
        "status": "installed-or-upgraded",
        "installed_version": latest.version,
        "verified_compatible": True,
        "installed_compatibility_reason": "within-policy",
        "webgpt_install_owned": True,
        "runtime_lifecycle_authority": False,
    }


def run_deploy(
    *,
    apply: bool = False,
    component_ids: list[str] | None = None,
    include_optional: bool = False,
    adopt_external: bool = False,
) -> dict[str, Any]:
    components = load_components()
    selected: list[Component] = []
    if component_ids:
        missing = sorted(set(component_ids) - set(components))
        if missing:
            return {"ok": False, "status": "unknown-components", "components": missing}
        selected = [components[cid] for cid in component_ids]
    else:
        selected = []
        for component in components.values():
            spec = install_spec(component)
            if (
                component.required
                or component.enabled_by_default
                or include_optional
                or (spec is not None and spec.strategy == "manual")
            ):
                selected.append(component)
    rows = [
        apply_component(component, adopt_external=adopt_external)
        if apply
        else plan_component(component)
        for component in sorted(selected, key=lambda item: item.id)
    ]
    blocking = [
        row
        for row in rows
        if row.get("blocking") is True
        or row.get("action", "").startswith("diagnose-")
        or row.get("action", "").startswith("install-blocked-")
    ]
    return {
        "ok": not blocking and all(row.get("ok", True) is not False for row in rows),
        "applied": apply,
        "adopt_external": adopt_external,
        "toolchain": toolchain_environment(),
        "components": rows,
        "blocking": [row["component_id"] for row in blocking],
        "preserve_existing_first": True,
    }


def cli_deploy(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="webgpt-codex deploy")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--component", action="append", default=[])
    parser.add_argument("--include-optional", action="store_true")
    parser.add_argument(
        "--adopt-external",
        action="store_true",
        help="upgrade a stopped older external install and record WebGPT install ownership",
    )
    args = parser.parse_args(argv)
    result = run_deploy(
        apply=args.apply,
        component_ids=args.component or None,
        include_optional=args.include_optional,
        adopt_external=args.adopt_external,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 2
