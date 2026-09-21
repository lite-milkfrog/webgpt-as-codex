from __future__ import annotations

import argparse
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL = REPO_ROOT / "skills" / "webgpt-as-codex"
DEFAULT_TARGET = REPO_ROOT.parent / ".skills" / "webgpt-as-codex"
LOCAL_OVERLAY_ROOT_FILES = {
    "environment.local.md",
    "MCP-SKILLS-INVENTORY.md",
    "MCP-SKILLS-INVENTORY.json",
}
LOCAL_OVERLAY_DIRS = {"state"}


def portable_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.is_file())


def sync_portable(target: Path) -> list[str]:
    copied: list[str] = []
    for source in portable_files(CANONICAL):
        relative = source.relative_to(CANONICAL)
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists() or destination.read_bytes() != source.read_bytes():
            shutil.copy2(source, destination)
            copied.append(relative.as_posix())
    return copied


def compare_portable(target: Path) -> list[str]:
    mismatches: list[str] = []
    for source in portable_files(CANONICAL):
        relative = source.relative_to(CANONICAL)
        destination = target / relative
        if not destination.is_file() or destination.read_bytes() != source.read_bytes():
            mismatches.append(relative.as_posix())
    return mismatches


def assert_canonical_is_portable() -> None:
    forbidden = [
        name for name in LOCAL_OVERLAY_ROOT_FILES if (CANONICAL / name).exists()
    ]
    forbidden.extend(
        name for name in LOCAL_OVERLAY_DIRS if (CANONICAL / name).exists()
    )
    if forbidden:
        raise SystemExit(
            "canonical WebGPT-as-Codex Skill contains machine-local overlay: "
            + ", ".join(sorted(forbidden))
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    assert_canonical_is_portable()
    target = args.target.expanduser().resolve()
    if args.check:
        mismatches = compare_portable(target)
        if mismatches:
            print("PORTABLE_SKILL_DRIFT")
            for value in mismatches:
                print(value)
            return 1
        print("PORTABLE_SKILL_SYNC_OK")
        return 0

    copied = sync_portable(target)
    print(f"PORTABLE_SKILL_SYNCED files={len(copied)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
