# Modified by WebGPT-as-Codex on 2026-09-27; see WAC_MODIFICATIONS.md.
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

from tests.compliance.mcp_client import StdioMCPClient
from tests.compliance.test_support import structured_payload


def has_msvc_environment() -> bool:
    return (
        sys.platform == "win32"
        and shutil.which("cl.exe") is not None
        and bool(os.environ.get("INCLUDE"))
        and bool(os.environ.get("LIB"))
    )


class WindowsProcessSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        if sys.platform != "win32":
            self.skipTest("requires Windows")

    def test_windows_tty_pipe_fallback_remains_interactive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            command = subprocess.list2cmdline(
                [
                    sys.executable,
                    "-u",
                    "-c",
                    (
                        "import sys,time; "
                        "print('TTY_READY', flush=True); "
                        "line=sys.stdin.readline().strip(); "
                        "print('TTY_GOT:'+line, flush=True); "
                        "time.sleep(0.2)"
                    ),
                ]
            )
            with StdioMCPClient(
                workspace,
                extra_args=["--permission-mode", "trusted"],
            ) as client:
                started = assert_tool_success(
                    self,
                    client.call_tool(
                        "exec_command",
                        {
                            "cmd": command,
                            "tty": True,
                            "timeout_ms": 5000,
                            "yield_time_ms": 300,
                        },
                    ),
                )
                self.assertIn(started.get("status"), {"running", "exited"}, started)
                self.assertIn("TTY_READY", started.get("stdout", ""), started)
                command_id = started.get("command_id")
                self.assertIsInstance(command_id, str, started)
                if started.get("status") == "running":
                    replied = assert_tool_success(
                        self,
                        client.call_tool(
                            "write_stdin",
                            {
                                "command_id": command_id,
                                "chars": "PING\n",
                                "yield_time_ms": 1000,
                            },
                        ),
                    )
                    self.assertIn("TTY_GOT:PING", replied.get("stdout", ""), replied)
                    settled = assert_tool_success(
                        self,
                        client.call_tool(
                            "write_stdin",
                            {
                                "command_id": command_id,
                                "chars": "",
                                "yield_time_ms": 1000,
                            },
                        ),
                    )
                    if settled.get("status") == "running":
                        assert_tool_success(
                            self,
                            client.call_tool(
                                "kill_command",
                                {"command_id": command_id, "signal": "KILL", "wait_ms": 3000},
                            ),
                        )

    def test_windows_search_text_handles_utf8_rg_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "馃摎-emoji.txt").write_text("needle 馃摎 unicode\n", encoding="utf-8")
            with StdioMCPClient(workspace) as client:
                result = assert_tool_success(
                    self,
                    client.call_tool(
                        "search_text",
                        {"query": "needle", "path": ".", "max_results": 10},
                    ),
                )
                self.assertEqual(result.get("total_matches"), 1, result)
                self.assertIn("馃摎", result.get("matches", [{}])[0].get("preview", ""), result)
                self.assertIn("馃摎", result.get("matches", [{}])[0].get("path", ""), result)

    def test_windows_nested_git_tools_use_nested_repository_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            nested = workspace / "nested"
            nested.mkdir()
            subprocess.run(["git", "init", "-q", str(nested)], check=True)
            subprocess.run(["git", "-C", str(nested), "config", "user.email", "smoke@example.test"], check=True)
            subprocess.run(["git", "-C", str(nested), "config", "user.name", "Smoke"], check=True)
            tracked = nested / "README.md"
            tracked.write_text("alpha\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(nested), "add", "README.md"], check=True)
            subprocess.run(["git", "-C", str(nested), "commit", "-q", "-m", "initial"], check=True)
            tracked.write_text("alpha\nbeta\n", encoding="utf-8")

            with StdioMCPClient(workspace) as client:
                log = assert_tool_success(
                    self,
                    client.call_tool("git_log", {"path": "nested", "max_count": 5}),
                )
                self.assertIs(log.get("is_repo"), True, log)
                self.assertTrue(log.get("commits"), log)

                show = assert_tool_success(
                    self,
                    client.call_tool(
                        "git_show",
                        {"path": "nested", "rev": "HEAD", "include_diff": False},
                    ),
                )
                self.assertIs(show.get("is_repo"), True, show)
                self.assertIn("initial", show.get("content", ""), show)

                blame = assert_tool_success(
                    self,
                    client.call_tool(
                        "git_blame",
                        {"path": "nested/README.md", "start_line": 1, "end_line": 1},
                    ),
                )
                self.assertIs(blame.get("is_repo"), True, blame)
                self.assertTrue(blame.get("lines"), blame)

                diff = assert_tool_success(
                    self,
                    client.call_tool("git_diff", {"path": "nested"}),
                )
                self.assertIn("+beta", diff.get("diff", ""), diff)

    def test_windows_force_kill_cleans_background_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            command = subprocess.list2cmdline(
                [sys.executable, "-c", "import time; time.sleep(30)"]
            )
            with StdioMCPClient(
                workspace,
                extra_args=["--permission-mode", "trusted"],
            ) as client:
                started = assert_tool_success(
                    self,
                    client.call_tool(
                        "exec_command",
                        {
                            "cmd": command,
                            "timeout_ms": 60_000,
                            "yield_time_ms": 0,
                        },
                    ),
                )
                self.assertEqual(started.get("status"), "running", started)
                command_id = started.get("command_id")
                self.assertIsInstance(command_id, str, started)

                killed = assert_tool_success(
                    self,
                    client.call_tool(
                        "kill_command",
                        {"command_id": command_id, "signal": "KILL", "wait_ms": 5000},
                    ),
                )
                self.assertIn(killed.get("status"), {"killed", "exited"}, killed)


class WindowsMsvcEnvironmentSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        if not has_msvc_environment():
            self.skipTest("requires Windows with vcvars initialized for cl.exe")

    def test_core_env_does_not_accidentally_inherit_msvc_toolchain(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            write_hello_c(workspace)
            with StdioMCPClient(workspace, extra_args=["--shell-env-inherit", "core"]) as client:
                info = structured_payload(client.call_tool("server_info", {}))
                self.assertEqual(info.get("shell_env_inherit"), "core")

                result = client.call_tool(
                    "exec_command",
                    {
                        "cmd": "cl.exe /nologo hello.c",
                        "timeout_ms": 30000,
                        "yield_time_ms": 30000,
                        "max_output_bytes": 20000,
                    },
                )
                payload = assert_tool_success(self, result)
                output = (payload.get("stdout") or "") + (payload.get("stderr") or "")
                self.assertNotEqual(payload.get("exit_code"), 0, output)
                self.assertFalse((workspace / "hello.exe").exists(), output)
                self.assertRegex(output.lower(), r"(stdio\.h|c1083|include|cannot open)")

    def test_inherit_all_preserves_msvc_environment_for_single_file_compile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            write_hello_c(workspace)
            with StdioMCPClient(workspace, extra_args=["--shell-env-inherit", "all"]) as client:
                info = structured_payload(client.call_tool("server_info", {}))
                self.assertEqual(info.get("shell_env_inherit"), "all")

                compile_result = client.call_tool(
                    "exec_command",
                    {
                        "cmd": "cl.exe /nologo hello.c",
                        "timeout_ms": 30000,
                        "yield_time_ms": 30000,
                        "max_output_bytes": 20000,
                    },
                )
                compile_payload = assert_tool_success(self, compile_result)
                compile_output = (compile_payload.get("stdout") or "") + (compile_payload.get("stderr") or "")
                self.assertEqual(compile_payload.get("exit_code"), 0, compile_output)
                self.assertTrue((workspace / "hello.exe").exists(), compile_output)

                run_result = client.call_tool(
                    "exec_command",
                    {
                        "cmd": "hello.exe",
                        "timeout_ms": 30000,
                        "yield_time_ms": 30000,
                        "max_output_bytes": 20000,
                    },
                )
                run_payload = assert_tool_success(self, run_result)
                self.assertEqual(run_payload.get("exit_code"), 0, run_payload)
                self.assertIn("ok", str(run_payload.get("stdout") or ""))

def write_hello_c(workspace: Path) -> None:
    (workspace / "hello.c").write_text(
        '#include <stdio.h>\n\nint main(void) {\n    puts("ok");\n    return 0;\n}\n',
        encoding="utf-8",
    )


def assert_tool_success(testcase: unittest.TestCase, result: dict[str, Any]) -> dict[str, Any]:
    testcase.assertFalse(result.get("isError", False), result)
    payload = structured_payload(result)
    testcase.assertIsInstance(payload, dict, result)
    return payload

