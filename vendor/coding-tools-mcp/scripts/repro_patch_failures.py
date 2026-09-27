#!/usr/bin/env python3
"""Regression guard for the `apply_patch` recovery protocol.

Each case is one shape a real model produced against a real file. The script
exits with the number of failing cases, so CI can treat "no case regressed"
as `exit 0` without parsing output.

Run it directly:

    python scripts/repro_patch_failures.py            # summary
    python scripts/repro_patch_failures.py --verbose  # plus the failure detail

The cases were originally written against v0.3.0, where four of the five
failed. They are kept as executable statements of the contract rather than as
a snapshot: a case that starts failing means a recovery affordance regressed.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from coding_tools_mcp.errors import ToolFailure  # noqa: E402
from coding_tools_mcp.server import Runtime  # noqa: E402


DUPLICATE_BODY = """def greet(name):
    print("hello")
    return None


def farewell(name):
    print("hello")
    return None
"""

INDENTED = """class Service:
    def run(self):
        value = compute()
        return value
"""

TAIL = """alpha
beta
gamma
"""


@dataclass
class Case:
    name: str
    why: str
    files: dict[str, str]
    patch: str
    expect_contains: dict[str, str] = field(default_factory=dict)
    expect_absent: dict[str, str] = field(default_factory=dict)
    expect_payload: dict[str, object] = field(default_factory=dict)


CASES: list[Case] = [
    Case(
        name="C2 scope anchor on the @@ line",
        why=(
            "`@@ def farewell` must select the second of two identical bodies. "
            "Parsed-and-discarded scope text made this PATCH_CONTEXT_AMBIGUOUS."
        ),
        files={"app.py": DUPLICATE_BODY},
        patch="""*** Begin Patch
*** Update File: app.py
@@ def farewell
-    print("hello")
+    print("bye")
*** End Patch
""",
        expect_contains={"app.py": 'def farewell(name):\n    print("bye")'},
        expect_absent={"app.py": 'def greet(name):\n    print("bye")'},
    ),
    Case(
        name="C4 trailing whitespace in a context line",
        why="One trailing space in context was a hard PATCH_CONTEXT_NOT_FOUND.",
        files={"app.py": "def greet(name):\n    print('hello')\n    return None\n"},
        patch="""*** Begin Patch
*** Update File: app.py
@@
 def greet(name): 
-    print('hello')
+    print('hi')
*** End Patch
""",
        expect_contains={"app.py": "print('hi')"},
        expect_payload={"match_quality": "trailing_ws"},
    ),
    Case(
        name="C4 indentation width drift",
        why="A hunk indented with a different width must still place, re-indented truthfully.",
        files={"svc.py": INDENTED},
        patch="""*** Begin Patch
*** Update File: svc.py
@@
 value = compute()
-return value
+return value * 2
*** End Patch
""",
        expect_contains={"svc.py": "        return value * 2"},
        expect_payload={"match_quality": "indent"},
    ),
    Case(
        name="*** End of File anchors the tail",
        why="`*** End of File` was parsed and ignored instead of acting as an EOF anchor.",
        files={"log.txt": "beta\nbeta\nbeta\n"},
        patch="""*** Begin Patch
*** Update File: log.txt
@@
-beta
+omega
*** End of File
*** End Patch
""",
        expect_contains={"log.txt": "beta\nbeta\nomega\n"},
    ),
    Case(
        name="C7 already-applied patch is not an error",
        why="Re-sending a patch after a lost response returned PATCH_CONTEXT_NOT_FOUND.",
        files={"app.py": "def run():\n    value = 2\n"},
        patch="""*** Begin Patch
*** Update File: app.py
@@
 def run():
-    value = 1
+    value = 2
*** End Patch
""",
        expect_contains={"app.py": "def run():\n    value = 2\n"},
        expect_payload={"already_applied": True},
    ),
    Case(
        name="C7 a common line elsewhere is not already-applied",
        why=(
            "An unanchored single line found anywhere in the file used to count as "
            "the hunk's result, turning a miss into a silent success."
        ),
        files={"app.py": "alpha\nx = 2\nbeta\n"},
        patch="""*** Begin Patch
*** Update File: app.py
@@
-x = 1
+x = 2
*** End Patch
""",
        expect_payload={"error_code": "PATCH_CONTEXT_NOT_FOUND", "has_nearby_text": True},
    ),
    Case(
        name="C7 blank-only context is not already-applied",
        why=(
            "A trailing blank line exists in every newline-terminated file and cannot prove "
            "that a deletion of text the file never contained already happened."
        ),
        files={"app.py": "unrelated\n"},
        patch=(
            "*** Begin Patch\n"
            "*** Update File: app.py\n"
            "@@\n"
            "-never existed\n"
            " \n"
            "*** End Patch\n"
        ),
        expect_payload={"error_code": "PATCH_CONTEXT_NOT_FOUND", "has_nearby_text": True},
    ),
    Case(
        name="D-2 same-path chaining inside one envelope",
        why="Two updates to one path chain on the prior staged content; this is a promise now.",
        files={"app.py": "one\ntwo\n"},
        patch="""*** Begin Patch
*** Update File: app.py
@@
-one
+ONE
*** Update File: app.py
@@
-two
+TWO
*** End Patch
""",
        expect_contains={"app.py": "ONE\nTWO\n"},
    ),
    Case(
        name="C5 failure carries repair data",
        why="A miss must name the hunk, the nearest text, and the line numbers around it.",
        files={"app.py": TAIL},
        patch="""*** Begin Patch
*** Update File: app.py
@@
-delta
+epsilon
*** End Patch
""",
        expect_payload={"error_code": "PATCH_CONTEXT_NOT_FOUND", "has_nearby_text": True},
    ),
]


def run_case(case: Case) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory() as raw_root:
        root = Path(raw_root)
        for name, body in case.files.items():
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding="utf-8")
        runtime = Runtime(root, permission_mode="safe")
        try:
            try:
                payload = runtime.apply_patch({"patch": case.patch})
                error_code = None
            except ToolFailure as failure:
                payload = {"error": failure.code, "details": failure.details}
                error_code = failure.code

            expected_error = case.expect_payload.get("error_code")
            if expected_error:
                if error_code != expected_error:
                    return False, f"expected {expected_error}, got {error_code or 'success'}"
                details = payload.get("details") or {}
                if case.expect_payload.get("has_nearby_text") and not details.get("nearby_text"):
                    return False, f"failure details carry no nearby_text: {details!r}"
                return True, "failed with repair data as required"
            if error_code is not None:
                return False, f"unexpected {error_code}: {payload.get('details')!r}"

            for name, needle in case.expect_contains.items():
                body = (root / name).read_text(encoding="utf-8")
                if needle not in body:
                    return False, f"{name} does not contain {needle!r}; got {body!r}"
            for name, needle in case.expect_absent.items():
                body = (root / name).read_text(encoding="utf-8")
                if needle in body:
                    return False, f"{name} unexpectedly contains {needle!r}"
            expected_quality = case.expect_payload.get("match_quality")
            if expected_quality:
                qualities = {
                    entry.get("match_quality")
                    for entry in payload.get("affected_files", [])
                    if isinstance(entry, dict)
                }
                if expected_quality not in qualities:
                    return False, f"expected match_quality {expected_quality}, got {sorted(map(str, qualities))}"
            if case.expect_payload.get("already_applied") and not payload.get("already_applied"):
                return False, f"expected already_applied, got {payload!r}"
            return True, "ok"
        finally:
            runtime.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--verbose", action="store_true", help="print why each case passed or failed")
    args = parser.parse_args(argv)

    failures = 0
    for case in CASES:
        ok, detail = run_case(case)
        if not ok:
            failures += 1
        status = "OK  " if ok else "FAIL"
        print(f"{status} {case.name}")
        if args.verbose or not ok:
            print(f"       why: {case.why}")
            print(f"       {detail}")
    print(f"\n{len(CASES) - failures}/{len(CASES)} cases OK")
    return failures


if __name__ == "__main__":
    raise SystemExit(main())
