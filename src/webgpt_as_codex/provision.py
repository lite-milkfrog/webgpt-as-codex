from __future__ import annotations

import hashlib
import os
import platform
import shutil
import tempfile
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .paths import ensure_state_dirs


@dataclass(frozen=True)
class ApprovedArtifact:
    component_id: str
    version: str
    architecture: str
    source_url: str
    sha256: str
    destination: str
    archive_member: str | None = None


_APPROVED: dict[tuple[str, str], ApprovedArtifact] = {
    (
        "mcpjungle",
        "amd64",
    ): ApprovedArtifact(
        component_id="mcpjungle",
        version="0.4.6",
        architecture="amd64",
        source_url=(
            "https://github.com/mcpjungle/MCPJungle/releases/download/"
            "0.4.6/mcpjungle_Windows_x86_64.zip"
        ),
        sha256="73d43850335bb1f7a02283038c6c7d31075b0c63d90a7ef01e89e602eee26216",
        destination="bin/mcpjungle/mcpjungle.exe",
        archive_member="mcpjungle.exe",
    ),
    (
        "mcpjungle",
        "arm64",
    ): ApprovedArtifact(
        component_id="mcpjungle",
        version="0.4.6",
        architecture="arm64",
        source_url=(
            "https://github.com/mcpjungle/MCPJungle/releases/download/"
            "0.4.6/mcpjungle_Windows_arm64.zip"
        ),
        sha256="e8061947551e80d0311f2074ac4260baaa01525a516c05ee614d75698ecef212",
        destination="bin/mcpjungle/mcpjungle.exe",
        archive_member="mcpjungle.exe",
    ),
    (
        "mcp-auth-proxy",
        "amd64",
    ): ApprovedArtifact(
        component_id="mcp-auth-proxy",
        version="2.10.2",
        architecture="amd64",
        source_url=(
            "https://github.com/sigbit/mcp-auth-proxy/releases/download/"
            "v2.10.2/mcp-auth-proxy-windows-amd64.exe"
        ),
        sha256="f64119236682f4f16adc025c69b1cea1c075ced24df0ed4fb52f22837c0ed3b5",
        destination="bin/mcp-auth-proxy/mcp-auth-proxy.exe",
    ),
    (
        "mcp-auth-proxy",
        "arm64",
    ): ApprovedArtifact(
        component_id="mcp-auth-proxy",
        version="2.10.2",
        architecture="arm64",
        source_url=(
            "https://github.com/sigbit/mcp-auth-proxy/releases/download/"
            "v2.10.2/mcp-auth-proxy-windows-arm64.exe"
        ),
        sha256="c20eff1c4f30c0e9cef2e297424de6363e9a318f2a2c65c20fa2c80f8530cbd7",
        destination="bin/mcp-auth-proxy/mcp-auth-proxy.exe",
    ),
}


def _architecture() -> str:
    raw = platform.machine().lower()
    if raw in {"amd64", "x86_64"}:
        return "amd64"
    if raw in {"arm64", "aarch64"}:
        return "arm64"
    raise RuntimeError(f"unsupported Windows architecture: {raw or 'unknown'}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _destination(artifact: ApprovedArtifact) -> Path:
    root = ensure_state_dirs().resolve()
    relative = Path(artifact.destination)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("approved destination must stay under the WebGPT state root")
    target = (root / relative).resolve()
    if root not in target.parents:
        raise ValueError("approved destination escaped the WebGPT state root")
    return target


def _download(artifact: ApprovedArtifact, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        artifact.source_url,
        headers={"User-Agent": "WebGPT-as-Codex/0.1"},
    )
    with urllib.request.urlopen(request, timeout=90) as response, target.open("wb") as handle:
        shutil.copyfileobj(response, handle)
    actual = _sha256(target)
    if actual != artifact.sha256:
        target.unlink(missing_ok=True)
        raise RuntimeError(
            f"{artifact.component_id} download SHA-256 mismatch: {actual}"
        )
    return target


def _stage_executable(artifact: ApprovedArtifact, downloaded: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, raw_temp = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".provision",
        dir=target.parent,
    )
    os.close(fd)
    temp = Path(raw_temp)
    try:
        if artifact.archive_member is None:
            shutil.copyfile(downloaded, temp)
        else:
            with zipfile.ZipFile(downloaded) as archive:
                names = archive.namelist()
                match = next(
                    (
                        name
                        for name in names
                        if Path(name).name.lower() == artifact.archive_member.lower()
                    ),
                    None,
                )
                if match is None:
                    raise RuntimeError(
                        f"{artifact.component_id} archive does not contain "
                        f"{artifact.archive_member}"
                    )
                info = archive.getinfo(match)
                if info.is_dir() or info.file_size <= 0 or info.file_size > 256 * 1024 * 1024:
                    raise RuntimeError("approved archive member has invalid size")
                with archive.open(info) as source, temp.open("wb") as destination:
                    shutil.copyfileobj(source, destination)
        if temp.stat().st_size <= 0:
            raise RuntimeError("provisioned executable is empty")
        os.replace(temp, target)
    finally:
        temp.unlink(missing_ok=True)


def provision_component(
    component_id: str,
    *,
    force: bool = False,
) -> dict[str, Any]:
    if os.name != "nt":
        return {
            "ok": False,
            "component_id": component_id,
            "status": "unsupported-platform",
        }
    arch = _architecture()
    artifact = _APPROVED.get((component_id, arch))
    if artifact is None:
        return {
            "ok": False,
            "component_id": component_id,
            "status": "no-approved-artifact",
            "architecture": arch,
        }

    return provision_artifact(artifact, force=force)


def provision_artifact(
    artifact: ApprovedArtifact,
    *,
    force: bool = False,
) -> dict[str, Any]:
    target = _destination(artifact)
    if target.is_file() and not force:
        return {
            "ok": True,
            "component_id": artifact.component_id,
            "status": "preserved-existing",
            "version": artifact.version,
            "destination": artifact.destination,
            "mutation": False,
        }

    download_root = (
        ensure_state_dirs()
        / "downloads"
        / "provision"
        / artifact.component_id
        / artifact.version
    )
    suffix = ".zip" if artifact.archive_member is not None else ".exe"
    downloaded = download_root / f"{artifact.component_id}-{artifact.architecture}{suffix}"

    if not downloaded.is_file() or _sha256(downloaded) != artifact.sha256:
        downloaded.unlink(missing_ok=True)
        _download(artifact, downloaded)

    if target.exists() and force:
        backup_root = ensure_state_dirs() / "runtime" / "provision-backups"
        backup_root.mkdir(parents=True, exist_ok=True)
        backup = backup_root / f"{target.name}.{artifact.component_id}.bak"
        shutil.copy2(target, backup)

    _stage_executable(artifact, downloaded, target)
    return {
        "ok": True,
        "component_id": artifact.component_id,
        "status": "provisioned",
        "version": artifact.version,
        "destination": artifact.destination,
        "source_url": artifact.source_url,
        "download_sha256": artifact.sha256,
        "mutation": True,
    }


def provision_runtime_binaries(*, force: bool = False) -> dict[str, Any]:
    results = [
        provision_component("mcpjungle", force=force),
        provision_component("mcp-auth-proxy", force=force),
    ]
    return {
        "ok": all(bool(item.get("ok")) for item in results),
        "preserves_existing_by_default": True,
        "results": results,
    }
