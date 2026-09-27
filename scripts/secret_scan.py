from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

PATTERNS = [
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(
        r"""(?ix)
        ["']?(password|client_secret|access_token|refresh_token)["']?
        \s*[:=]\s*
        ["']([^"'\s]{12,})["']
        """
    ),
]
ALLOW = {".gitignore", "scripts/secret_scan.py"}
VENDOR_DERIVATIVE_FILES = {
    "vendor/coding-tools-mcp/apps/desktop-client/mcp_desktop_client/language_manager.py",
    "vendor/coding-tools-mcp/apps/desktop-client/mcp_desktop_client/storage.py",
    "vendor/coding-tools-mcp/coding_tools_mcp/processes.py",
    "vendor/coding-tools-mcp/coding_tools_mcp/server.py",
    "vendor/coding-tools-mcp/tests/compliance/test_windows_msvc_smoke.py",
    "vendor/serena-agent/src/serena/tools/symbol_tools.py",
}
PLACEHOLDER_SECRET_VALUES = {"secret-value"}


def should_scan(rel: str) -> bool:
    if not rel.startswith("vendor/"):
        return True
    path = Path(rel)
    return rel in VENDOR_DERIVATIVE_FILES or path.name.startswith("WAC_")


def contains_secret(text: str) -> bool:
    if PATTERNS[0].search(text):
        return True
    for match in PATTERNS[1].finditer(text):
        if match.group(2).casefold() not in PLACEHOLDER_SECRET_VALUES:
            return True
    return False


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    files = subprocess.check_output(["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard"], text=True).splitlines()
    bad: list[str] = []
    for rel in files:
        if rel in ALLOW or not should_scan(rel):
            continue
        path = root / rel
        if not path.is_file() or path.stat().st_size > 2_000_000:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if contains_secret(text):
            bad.append(rel)
    if bad:
        print("SECRET_SCAN_FAIL")
        for rel in bad:
            print(rel)
        return 1
    print("SECRET_SCAN_PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
