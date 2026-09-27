from __future__ import annotations

import argparse
import io
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from coding_tools_mcp import server as server_module
from coding_tools_mcp.server import (
    Runtime,
    WorkspaceMutationPolicy,
    build_parser,
    open_landlock_ruleset,
    run_stdio,
    runtime_policy_from_args,
    workspace_mutation_policy_from_args,
)


def parse(argv: list[str]) -> argparse.Namespace:
    return build_parser().parse_args(argv)


class WorkspaceMutationArgumentTests(unittest.TestCase):
    def test_the_default_is_unrestricted(self) -> None:
        policy = workspace_mutation_policy_from_args(parse([]))
        self.assertEqual(policy.mode, "unrestricted")
        self.assertFalse(policy.structured_only)
        self.assertEqual(policy.write_paths, ())

    def test_structured_only_collects_repeated_write_paths(self) -> None:
        policy = workspace_mutation_policy_from_args(
            parse(
                [
                    "--workspace-mutation",
                    "structured-only",
                    "--write-path",
                    "build",
                    "--write-path",
                    ".pytest_cache",
                ]
            )
        )
        self.assertTrue(policy.structured_only)
        self.assertEqual(policy.write_paths, ("build", ".pytest_cache"))

    def test_a_write_path_without_the_mode_is_a_startup_error(self) -> None:
        # Silently ignoring it would let an operator believe a directory is
        # exempt from a restriction that is not even on.
        with self.assertRaises(ValueError):
            workspace_mutation_policy_from_args(parse(["--write-path", "build"]))

    def test_an_unknown_mode_is_rejected(self) -> None:
        args = parse([])
        args.workspace_mutation = "read-only"
        with self.assertRaises(ValueError):
            workspace_mutation_policy_from_args(args)

    def test_the_runtime_policy_carries_the_mutation_policy(self) -> None:
        policy = runtime_policy_from_args(parse(["--workspace-mutation", "structured-only"]))
        self.assertTrue(policy.workspace_mutation.structured_only)


class WorkspaceMutationRuntimeTests(unittest.TestCase):
    def runtime(self, workspace: Path, **fields: object) -> Runtime:
        return Runtime(workspace, workspace_mutation=WorkspaceMutationPolicy(**fields))

    def test_the_default_policy_is_disclosed_as_unrestricted(self) -> None:
        with TemporaryDirectory() as tmp:
            runtime = Runtime(Path(tmp))
            try:
                payload = runtime.server_info_payload()["workspace_mutation_policy"]
                self.assertEqual(payload["mode"], "unrestricted")
                self.assertIs(payload["enforced"], True)
                self.assertIn("apply_changes", payload["structured_write_tools"])
            finally:
                runtime.close()

    def test_write_paths_are_resolved_inside_the_workspace(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "build").mkdir()
            runtime = self.runtime(workspace, mode="structured-only", write_paths=("build",))
            try:
                self.assertEqual(runtime.workspace_write_paths(), [(workspace / "build").resolve()])
                self.assertIn(
                    (workspace / "build").resolve(), runtime.landlock_write_roots()
                )
            finally:
                runtime.close()

    def test_reporting_a_missing_write_path_does_not_create_it(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            runtime = self.runtime(
                workspace,
                mode="structured-only",
                write_paths=("generated/nested",),
            )
            try:
                payload = runtime.workspace_mutation_payload()
                expected = (workspace / "generated" / "nested").resolve()
                self.assertFalse(expected.exists())
                self.assertEqual(runtime.workspace_write_paths(), [expected])
                self.assertEqual(payload["write_paths"], ["generated/nested"])
                runtime.server_info_payload()
                runtime.check_exec_environment({})
                self.assertFalse(expected.exists())
            finally:
                runtime.close()

    def test_landlock_initialization_creates_a_missing_write_path(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            expected = workspace / "generated" / "nested"
            runtime = self.runtime(
                workspace,
                mode="structured-only",
                write_paths=("generated/nested",),
            )
            try:
                with patch.object(runtime, "landlock_enabled", return_value=True), patch(
                    f"{open_landlock_ruleset.__module__}.open_landlock_ruleset"
                ) as ruleset:
                    ruleset.side_effect = RuntimeError("stop after the ruleset is described")
                    with self.assertRaises(RuntimeError):
                        runtime.exec_command({"cmd": "true"})
                self.assertTrue(expected.is_dir())
                self.assertIn(expected.resolve(), ruleset.call_args.kwargs["write_roots"])
            finally:
                runtime.close()

    def test_a_write_path_that_is_a_file_is_a_clean_cli_error(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "build").write_text("not a directory", encoding="utf-8")
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                status = run_stdio(
                    parse(
                        [
                            "--stdio",
                            "--workspace",
                            str(workspace),
                            "--workspace-mutation",
                            "structured-only",
                            "--write-path",
                            "build",
                        ]
                    )
                )
        self.assertEqual(status, 2)
        self.assertIn("INVALID_ARGUMENT", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_a_write_path_outside_the_workspace_is_dropped(self) -> None:
        with TemporaryDirectory() as tmp:
            runtime = self.runtime(Path(tmp), mode="structured-only", write_paths=("../elsewhere", "/etc"))
            try:
                self.assertEqual(runtime.workspace_write_paths(), [])
            finally:
                runtime.close()

    def test_an_unenforceable_policy_says_so_instead_of_promising(self) -> None:
        with TemporaryDirectory() as tmp:
            runtime = self.runtime(Path(tmp), mode="structured-only")
            try:
                with patch.object(runtime, "landlock_enabled", return_value=False):
                    payload = runtime.workspace_mutation_payload()
                    self.assertEqual(payload["mode"], "structured-only")
                    self.assertIs(payload["enforced"], False)
                    warnings = runtime.check_exec_environment({})["warnings"]
                self.assertTrue(
                    any("structured-only is not enforced" in item for item in warnings), warnings
                )
            finally:
                runtime.close()

    def test_landlock_before_abi_three_does_not_claim_truncate_enforcement(self) -> None:
        with TemporaryDirectory() as tmp:
            runtime = self.runtime(Path(tmp), mode="structured-only")
            try:
                with patch.object(
                    server_module,
                    "landlock_status_payload",
                    return_value={"available": True, "abi_version": 2},
                ):
                    payload = runtime.workspace_mutation_payload()
                    checked = runtime.check_exec_environment({})
            finally:
                runtime.close()
        self.assertIs(payload["enforced"], False)
        self.assertEqual(payload["enforced_by"], "none")
        self.assertTrue(any("cannot deny file truncation" in item for item in payload["warnings"]))
        self.assertTrue(any("cannot deny file truncation" in item for item in checked["warnings"]))

    def test_structured_only_asks_landlock_for_a_read_only_workspace(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "build").mkdir()
            runtime = self.runtime(workspace, mode="structured-only", write_paths=("build",))
            try:
                with patch.object(runtime, "landlock_enabled", return_value=True), patch(
                    f"{open_landlock_ruleset.__module__}.open_landlock_ruleset"
                ) as ruleset:
                    ruleset.side_effect = RuntimeError("stop after the ruleset is described")
                    with self.assertRaises(RuntimeError):
                        runtime.exec_command({"cmd": "true"})
                self.assertIs(ruleset.call_args.kwargs["workspace_writable"], False)
                self.assertIn((workspace / "build").resolve(), ruleset.call_args.kwargs["write_roots"])
            finally:
                runtime.close()

    def test_unrestricted_leaves_the_workspace_writable_for_commands(self) -> None:
        with TemporaryDirectory() as tmp:
            runtime = Runtime(Path(tmp))
            try:
                with patch.object(runtime, "landlock_enabled", return_value=True), patch(
                    f"{open_landlock_ruleset.__module__}.open_landlock_ruleset"
                ) as ruleset:
                    ruleset.side_effect = RuntimeError("stop after the ruleset is described")
                    with self.assertRaises(RuntimeError):
                        runtime.exec_command({"cmd": "true"})
                self.assertIs(ruleset.call_args.kwargs["workspace_writable"], True)
            finally:
                runtime.close()


if __name__ == "__main__":
    unittest.main()
