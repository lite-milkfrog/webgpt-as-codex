from __future__ import annotations

import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from coding_tools_mcp import server as server_module
from coding_tools_mcp.breaker import RepeatFailureBreaker, argument_fingerprint
from coding_tools_mcp.errors import ToolFailure
from coding_tools_mcp.server import Runtime, WorkspaceMutationPolicy


class ArgumentFingerprintTests(unittest.TestCase):
    def test_key_order_does_not_change_the_fingerprint(self) -> None:
        self.assertEqual(
            argument_fingerprint({"path": "a.txt", "start_line": 1}),
            argument_fingerprint({"start_line": 1, "path": "a.txt"}),
        )

    def test_a_different_value_is_a_different_call(self) -> None:
        self.assertNotEqual(
            argument_fingerprint({"path": "a.txt"}),
            argument_fingerprint({"path": "b.txt"}),
        )

    def test_varying_only_the_idempotency_key_does_not_dodge_the_breaker(self) -> None:
        self.assertEqual(
            argument_fingerprint({"patch": "p", "idempotency_key": "one"}),
            argument_fingerprint({"patch": "p", "idempotency_key": "two"}),
        )

    def test_unserializable_arguments_still_produce_a_fingerprint(self) -> None:
        self.assertIsInstance(argument_fingerprint({"value": object()}), str)


class RepeatFailureBreakerTests(unittest.TestCase):
    def test_the_third_identical_deterministic_failure_is_refused(self) -> None:
        breaker = RepeatFailureBreaker()
        self.assertIsNone(breaker.blocked_error_code("read_file", "fp"))
        breaker.record_failure("read_file", "fp", error_code="NOT_FOUND", retryable=False)
        self.assertIsNone(breaker.blocked_error_code("read_file", "fp"))
        breaker.record_failure("read_file", "fp", error_code="NOT_FOUND", retryable=False)
        self.assertEqual(breaker.blocked_error_code("read_file", "fp"), "NOT_FOUND")

    def test_a_retryable_failure_never_counts(self) -> None:
        breaker = RepeatFailureBreaker()
        for _ in range(5):
            breaker.record_failure("apply_patch", "fp", error_code="PATCH_CONFLICT", retryable=True)
        self.assertIsNone(breaker.blocked_error_code("apply_patch", "fp"))

    def test_a_success_with_the_same_arguments_clears_the_count(self) -> None:
        breaker = RepeatFailureBreaker()
        breaker.record_failure("read_file", "fp", error_code="NOT_FOUND", retryable=False)
        breaker.record_failure("read_file", "fp", error_code="NOT_FOUND", retryable=False)
        breaker.record_success("read_file", "fp")
        self.assertIsNone(breaker.blocked_error_code("read_file", "fp"))

    def test_different_arguments_have_their_own_budget(self) -> None:
        breaker = RepeatFailureBreaker()
        for _ in range(3):
            breaker.record_failure("read_file", "one", error_code="NOT_FOUND", retryable=False)
        self.assertIsNone(breaker.blocked_error_code("read_file", "two"))

    def test_the_entry_map_stays_bounded(self) -> None:
        breaker = RepeatFailureBreaker(capacity=4)
        for index in range(20):
            breaker.record_failure("read_file", f"fp{index}", error_code="NOT_FOUND", retryable=False)
        self.assertLessEqual(len(breaker._entries), 4)


class BreakerInRuntimeTests(unittest.TestCase):
    def call(self, runtime: Runtime, args: dict[str, object]) -> dict[str, object]:
        return runtime.call_tool("read_file", args)

    def test_a_verbatim_retry_loop_terminates_with_a_distinct_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Runtime(Path(tmp), permission_mode="safe")
            try:
                args = {"path": "missing.txt"}
                first = self.call(runtime, args)
                second = self.call(runtime, args)
                third = self.call(runtime, args)
            finally:
                runtime.close()
        self.assertEqual(first["structuredContent"]["error"]["code"], "NOT_FOUND")
        # The second failure already warns that the next one will be refused.
        self.assertEqual(second["structuredContent"]["error"]["details"]["consecutive_identical_failures"], 2)
        self.assertEqual(third["structuredContent"]["error"]["code"], "REPEATED_CALL_BLOCKED")
        self.assertIs(third["structuredContent"]["error"]["retryable"], False)
        self.assertIn("REPEATED_CALL_BLOCKED", third["content"][0]["text"])

    def test_a_returned_ok_false_payload_counts_as_a_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Runtime(Path(tmp), permission_mode="safe")
            args = {
                "tool_name": "exec_command",
                "permission": "network",
                "reason": "breaker regression",
                "arguments": {"cmd": "curl https://example.com"},
            }
            try:
                first = runtime.call_tool("request_permissions", args)
                second = runtime.call_tool("request_permissions", args)
                third = runtime.call_tool("request_permissions", args)
            finally:
                runtime.close()
        self.assertEqual(first["structuredContent"]["error"]["code"], "ELICITATION_UNSUPPORTED")
        self.assertEqual(
            second["structuredContent"]["error"]["details"]["consecutive_identical_failures"],
            2,
        )
        self.assertEqual(third["structuredContent"]["error"]["code"], "REPEATED_CALL_BLOCKED")

    def test_revision_required_needs_a_changed_call_to_retry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "a.txt").write_text("old\n", encoding="utf-8")
            runtime = Runtime(workspace, permission_mode="safe")
            args = {
                "changes": [{"action": "write", "path": "a.txt", "content": "new\n"}]
            }
            try:
                first = runtime.call_tool("apply_changes", args)
                second = runtime.call_tool("apply_changes", args)
                third = runtime.call_tool("apply_changes", args)
            finally:
                runtime.close()
        self.assertEqual(first["structuredContent"]["error"]["code"], "REVISION_REQUIRED")
        self.assertEqual(
            second["structuredContent"]["error"]["details"]["consecutive_identical_failures"],
            2,
        )
        self.assertEqual(third["structuredContent"]["error"]["code"], "REPEATED_CALL_BLOCKED")

    def test_changing_the_arguments_is_never_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Runtime(Path(tmp), permission_mode="safe")
            try:
                for _ in range(3):
                    self.call(runtime, {"path": "missing.txt"})
                other = self.call(runtime, {"path": "also-missing.txt"})
            finally:
                runtime.close()
        self.assertEqual(other["structuredContent"]["error"]["code"], "NOT_FOUND")

    def test_a_write_that_lands_makes_every_earlier_verdict_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Runtime(Path(tmp), permission_mode="safe")
            try:
                self.call(runtime, {"path": "late.txt"})
                self.call(runtime, {"path": "late.txt"})
                self.assertEqual(
                    self.call(runtime, {"path": "late.txt"})["structuredContent"]["error"]["code"],
                    "REPEATED_CALL_BLOCKED",
                )
                created = runtime.call_tool(
                    "apply_patch",
                    {"patch": "*** Begin Patch\n*** Add File: late.txt\n+here\n*** End Patch\n"},
                )
                self.assertFalse(created["isError"])
                self.assertFalse(self.call(runtime, {"path": "late.txt"})["isError"])
            finally:
                runtime.close()

    def test_a_write_tool_with_no_net_mutation_keeps_earlier_verdicts(self) -> None:
        for tool_name in ("apply_patch", "apply_changes"):
            with self.subTest(tool=tool_name), tempfile.TemporaryDirectory() as tmp:
                workspace = Path(tmp)
                path = workspace / "app.py"
                path.write_text("one\ntwo\n", encoding="utf-8")
                runtime = Runtime(workspace, permission_mode="safe")
                missing_args = {"path": "missing.txt"}
                if tool_name == "apply_patch":
                    write_args: dict[str, object] = {
                        "patch": (
                            "*** Begin Patch\n"
                            "*** Update File: app.py\n"
                            "@@\n"
                            "-one\n"
                            "+ONE\n"
                            "*** Update File: app.py\n"
                            "@@\n"
                            "-ONE\n"
                            "+one\n"
                            "*** End Patch\n"
                        )
                    }
                else:
                    write_args = {
                        "changes": [
                            {
                                "action": "write",
                                "path": "app.py",
                                "revision": server_module.content_revision("one\ntwo\n"),
                                "content": "one\ntwo\n",
                            }
                        ]
                    }
                try:
                    self.call(runtime, missing_args)
                    self.call(runtime, missing_args)
                    before = path.stat().st_mtime_ns
                    no_op = runtime.call_tool(tool_name, write_args)
                    third = self.call(runtime, missing_args)
                finally:
                    runtime.close()
                self.assertFalse(no_op["isError"], no_op)
                self.assertEqual(path.read_text(encoding="utf-8"), "one\ntwo\n")
                self.assertEqual(path.stat().st_mtime_ns, before)
                self.assertTrue(
                    all(
                        entry["operation"] == "unchanged"
                        for entry in no_op["structuredContent"]["affected_files"]
                    )
                )
                self.assertEqual(
                    third["structuredContent"]["error"]["code"],
                    "REPEATED_CALL_BLOCKED",
                )

    def test_failures_started_before_a_reset_do_not_strike_the_new_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Runtime(Path(tmp), permission_mode="safe")
            original = runtime._tool_handlers["read_file"]
            all_entered = threading.Event()
            release = threading.Event()
            count_lock = threading.Lock()
            entered = 0

            def delayed(arguments: dict[str, object]) -> dict[str, object]:
                nonlocal entered
                with count_lock:
                    entered += 1
                    if entered == 2:
                        all_entered.set()
                if not release.wait(timeout=2):
                    raise RuntimeError("timed out waiting for breaker reset")
                return original(arguments)

            runtime._tool_handlers["read_file"] = delayed
            old_results: list[dict[str, object] | None] = [None, None]

            def read_missing(index: int) -> None:
                old_results[index] = self.call(runtime, {"path": "missing.txt"})

            threads = [
                threading.Thread(target=read_missing, args=(0,)),
                threading.Thread(target=read_missing, args=(1,)),
            ]
            try:
                for thread in threads:
                    thread.start()
                self.assertTrue(all_entered.wait(timeout=1))
                write = runtime.call_tool(
                    "apply_patch",
                    {"patch": "*** Begin Patch\n*** Add File: reset.txt\n+new\n*** End Patch\n"},
                )
                self.assertFalse(write["isError"], write)
            finally:
                release.set()
                for thread in threads:
                    thread.join(timeout=2)

            runtime._tool_handlers["read_file"] = original
            try:
                self.assertTrue(all(not thread.is_alive() for thread in threads))
                self.assertTrue(
                    all(
                        result is not None
                        and result["structuredContent"]["error"]["code"] == "NOT_FOUND"
                        for result in old_results
                    )
                )
                fresh = self.call(runtime, {"path": "missing.txt"})
                self.assertEqual(fresh["structuredContent"]["error"]["code"], "NOT_FOUND")
            finally:
                runtime.close()

    def test_an_already_applied_update_that_moves_the_file_is_a_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            source = workspace / "source.txt"
            source.write_text("anchor\nnew\n", encoding="utf-8")
            runtime = Runtime(workspace, permission_mode="safe")
            destination_args = {"path": "destination.txt"}
            try:
                self.call(runtime, destination_args)
                self.call(runtime, destination_args)
                moved = runtime.call_tool(
                    "apply_patch",
                    {
                        "patch": (
                            "*** Begin Patch\n"
                            "*** Update File: source.txt\n"
                            "*** Move to: destination.txt\n"
                            "@@\n"
                            " anchor\n"
                            "-old\n"
                            "+new\n"
                            "*** End Patch\n"
                        )
                    },
                )
                read = self.call(runtime, destination_args)
                source_exists_after_move = source.exists()
            finally:
                runtime.close()
        self.assertFalse(moved["isError"], moved)
        self.assertIs(moved["structuredContent"]["already_applied"], False)
        self.assertEqual(moved["structuredContent"]["affected_files"][0]["operation"], "move")
        self.assertFalse(source_exists_after_move)
        self.assertFalse(read["isError"], read)
        self.assertEqual(read["structuredContent"]["content"], "anchor\nnew\n")

    def test_a_completed_exec_makes_workspace_read_verdicts_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Runtime(Path(tmp), permission_mode="trusted")
            try:
                self.call(runtime, {"path": "late.txt"})
                self.call(runtime, {"path": "late.txt"})
                command = runtime.call_tool(
                    "exec_command",
                    {
                        "cmd": "printf 'created\\n' > late.txt",
                        "yield_time_ms": 5000,
                        "timeout_ms": 5000,
                    },
                )
                read = self.call(runtime, {"path": "late.txt"})
            finally:
                runtime.close()
        self.assertFalse(command["isError"], command)
        self.assertEqual(command["structuredContent"]["operation_outcome"], "exited_0")
        self.assertFalse(read["isError"], read)

    def test_a_terminal_write_stdin_poll_makes_workspace_read_verdicts_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Runtime(Path(tmp), permission_mode="trusted")
            command_text = (
                f'"{sys.executable}" -c "import time; time.sleep(0.2); '
                "open('late.txt', 'w').write('created\\\\n')\""
            )
            try:
                self.call(runtime, {"path": "late.txt"})
                self.call(runtime, {"path": "late.txt"})
                command = runtime.call_tool(
                    "exec_command",
                    {"cmd": command_text, "yield_time_ms": 1, "timeout_ms": 5000},
                )
                self.assertEqual(command["structuredContent"]["operation_outcome"], "running")
                poll: dict[str, object] = {}
                for _ in range(20):
                    poll = runtime.call_tool(
                        "write_stdin",
                        {
                            "command_id": command["structuredContent"]["command_id"],
                            "chars": "",
                            "yield_time_ms": 250,
                        },
                    )
                    if poll["structuredContent"]["operation_outcome"] != "running":
                        break
                read = self.call(runtime, {"path": "late.txt"})
            finally:
                runtime.close()
        self.assertEqual(poll["structuredContent"]["operation_outcome"], "exited_0")
        self.assertFalse(read["isError"], read)

    def test_every_terminal_command_observer_can_clear_stale_verdicts(self) -> None:
        arguments = {
            "write_stdin": {"command_id": "observed", "chars": ""},
            "read_output": {"output_ref": "command:observed:stdout"},
            "kill_command": {"command_id": "observed"},
        }
        for tool_name, tool_args in arguments.items():
            with self.subTest(tool=tool_name), tempfile.TemporaryDirectory() as tmp:
                workspace = Path(tmp)
                runtime = Runtime(workspace, permission_mode="trusted")
                try:
                    self.call(runtime, {"path": "late.txt"})
                    self.call(runtime, {"path": "late.txt"})
                    (workspace / "late.txt").write_text("created\n", encoding="utf-8")
                    runtime._tool_handlers[tool_name] = lambda _args: {
                        "command_id": "observed",
                        "operation_outcome": "exited_0",
                    }
                    observed = runtime.call_tool(tool_name, tool_args)
                    read = self.call(runtime, {"path": "late.txt"})
                finally:
                    runtime.close()
                self.assertFalse(observed["isError"], observed)
                self.assertFalse(read["isError"], read)

    def test_a_terminal_command_resets_the_breaker_only_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "a.txt").write_text("present\n", encoding="utf-8")
            runtime = Runtime(workspace, permission_mode="trusted")
            patch_args = {
                "patch": (
                    "*** Begin Patch\n"
                    "*** Update File: a.txt\n"
                    "@@\n"
                    "-missing\n"
                    "+replacement\n"
                    "*** End Patch\n"
                )
            }
            try:
                command = runtime.call_tool(
                    "exec_command",
                    {
                        "cmd": f'"{sys.executable}" -c "print(\'done\')"',
                        "yield_time_ms": 5000,
                        "timeout_ms": 5000,
                        "verbosity": "summary",
                    },
                )
                self.assertEqual(command["structuredContent"]["operation_outcome"], "exited_0")
                output_ref = command["structuredContent"]["output_refs"]["stdout"]

                first = runtime.call_tool("apply_patch", patch_args)
                runtime.call_tool("read_output", {"output_ref": output_ref})
                second = runtime.call_tool("apply_patch", patch_args)
                runtime.call_tool("read_output", {"output_ref": output_ref})
                third = runtime.call_tool("apply_patch", patch_args)
            finally:
                runtime.close()
        self.assertEqual(first["structuredContent"]["error"]["code"], "PATCH_CONTEXT_NOT_FOUND")
        self.assertEqual(second["structuredContent"]["error"]["code"], "PATCH_CONTEXT_NOT_FOUND")
        self.assertEqual(third["structuredContent"]["error"]["code"], "REPEATED_CALL_BLOCKED")

    def test_a_structured_only_command_with_a_write_path_clears_stale_verdicts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            runtime = Runtime(
                workspace,
                permission_mode="trusted",
                workspace_mutation=WorkspaceMutationPolicy(
                    mode="structured-only", write_paths=("generated",)
                ),
            )
            try:
                args = {"path": "generated/late.txt"}
                self.call(runtime, args)
                self.call(runtime, args)
                command = runtime.call_tool(
                    "exec_command",
                    {
                        "cmd": "printf 'created\\n' > generated/late.txt",
                        "yield_time_ms": 5000,
                        "timeout_ms": 5000,
                    },
                )
                read = self.call(runtime, args)
            finally:
                runtime.close()
        self.assertEqual(command["structuredContent"]["operation_outcome"], "exited_0")
        self.assertFalse(read["isError"], read)

    def test_a_structured_only_command_without_a_write_path_keeps_verdicts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Runtime(
                Path(tmp),
                permission_mode="trusted",
                workspace_mutation=WorkspaceMutationPolicy(mode="structured-only"),
            )
            try:
                args = {"path": "late.txt"}
                self.call(runtime, args)
                self.call(runtime, args)
                command = runtime.call_tool(
                    "exec_command",
                    {
                        "cmd": f'"{sys.executable}" -c "pass"',
                        "yield_time_ms": 5000,
                        "timeout_ms": 5000,
                    },
                )
                read = self.call(runtime, args)
            finally:
                runtime.close()
        self.assertEqual(command["structuredContent"]["operation_outcome"], "exited_0")
        self.assertEqual(read["structuredContent"]["error"]["code"], "REPEATED_CALL_BLOCKED")

    def test_unenforced_structured_only_mode_clears_stale_verdicts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            runtime = Runtime(
                workspace,
                permission_mode="dangerous",
                workspace_mutation=WorkspaceMutationPolicy(mode="structured-only"),
            )
            try:
                mutation = runtime.workspace_mutation_payload()
                self.assertEqual(mutation["mode"], "structured-only")
                self.assertIs(mutation["enforced"], False)
                args = {"path": "late.txt"}
                self.call(runtime, args)
                self.call(runtime, args)
                command = runtime.call_tool(
                    "exec_command",
                    {
                        "cmd": "printf 'created\\n' > late.txt",
                        "yield_time_ms": 5000,
                        "timeout_ms": 5000,
                    },
                )
                read = self.call(runtime, args)
            finally:
                runtime.close()
        self.assertEqual(command["structuredContent"]["operation_outcome"], "exited_0")
        self.assertFalse(read["isError"], read)

    def test_landlock_install_failure_clears_stale_verdicts_for_that_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            runtime = Runtime(
                workspace,
                permission_mode="trusted",
                workspace_mutation=WorkspaceMutationPolicy(mode="structured-only"),
            )

            def unavailable(*_args: object, **_kwargs: object) -> int:
                raise ToolFailure(
                    "SANDBOX_UNAVAILABLE",
                    "simulated Landlock install failure",
                    category="security",
                )

            args = {"path": "late.txt"}
            try:
                self.call(runtime, args)
                self.call(runtime, args)
                with patch.object(
                    server_module,
                    "landlock_status_payload",
                    return_value={"available": True, "abi_version": 6},
                ), patch.object(server_module, "open_landlock_ruleset", side_effect=unavailable):
                    self.assertIs(runtime.workspace_mutation_payload()["enforced"], True)
                    command = runtime.call_tool(
                        "exec_command",
                        {
                            "cmd": "printf 'created\\n' > late.txt",
                            "yield_time_ms": 5000,
                            "timeout_ms": 5000,
                        },
                    )
                read = self.call(runtime, args)
            finally:
                runtime.close()
        self.assertEqual(command["structuredContent"]["operation_outcome"], "exited_0")
        self.assertTrue(
            any("Landlock" in item for item in command["structuredContent"].get("warnings", []))
        )
        self.assertFalse(read["isError"], read)

    def test_a_dry_run_changes_nothing_and_does_not_clear_the_breaker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Runtime(Path(tmp), permission_mode="safe")
            try:
                self.call(runtime, {"path": "late.txt"})
                self.call(runtime, {"path": "late.txt"})
                runtime.call_tool(
                    "apply_patch",
                    {
                        "patch": "*** Begin Patch\n*** Add File: other.txt\n+x\n*** End Patch\n",
                        "dry_run": True,
                    },
                )
                self.assertEqual(
                    self.call(runtime, {"path": "late.txt"})["structuredContent"]["error"]["code"],
                    "REPEATED_CALL_BLOCKED",
                )
            finally:
                runtime.close()

    def test_a_verbatim_patch_context_miss_counts_even_though_it_is_retryable(self) -> None:
        breaker = RepeatFailureBreaker()
        for _ in range(2):
            breaker.record_failure(
                "apply_patch", "fp", error_code="PATCH_CONTEXT_NOT_FOUND", retryable=True
            )
        self.assertEqual(breaker.blocked_error_code("apply_patch", "fp"), "PATCH_CONTEXT_NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
