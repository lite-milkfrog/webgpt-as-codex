from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

PATTERNS = [
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)(password|client_secret|access_token|refresh_token)\s*[:=]\s*['\"]?[^\s'\"]{12,}"),
]
ALLOW = {".gitignore", "scripts/secret_scan.py"}


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    files = subprocess.check_output(["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard"], text=True).splitlines()
    bad: list[str] = []
    for rel in files:
        if rel in ALLOW:
            continue
        path = root / rel
        if not path.is_file() or path.stat().st_size > 2_000_000:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(p.search(text) for p in PATTERNS):
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
