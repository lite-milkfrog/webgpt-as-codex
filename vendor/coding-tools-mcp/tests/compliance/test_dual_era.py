"""Dual-era compliance: what the two protocol eras owe each other.

The precise per-error paths of `2026-07-28` live in `test_mcp_contract`. This
suite covers what only shows up once both eras share one server: that a
handshake-era response is still shaped exactly as it was, that concurrent
clients of either era reach neither into each other's answers nor into the
workspace state they share, and that the official python SDK — the one client
we did not write — can drive this server over both transports.
"""

from __future__ import annotations

import asyncio
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import unittest
import urllib.error
import urllib.request
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from coding_tools_mcp.server import Runtime
from tests.compliance.fixtures import FixtureWorkspace, workspace_from_fixture
from tests.compliance.mcp_client import prepend_repo_pythonpath, safe_server_env
from tests.compliance.test_support import ComplianceTestCase, structured_payload


LEGACY_PROTOCOL_VERSION = "2025-11-25"
MODERN_PROTOCOL_VERSION = "2026-07-28"
META_PROTOCOL_VERSION = "io.modelcontextprotocol/protocolVersion"
META_CLIENT_CAPABILITIES = "io.modelcontextprotocol/clientCapabilities"
META_SERVER_INFO = "io.modelcontextprotocol/serverInfo"
MODERN_META_PREFIX = "io.modelcontextprotocol/"
MODERN_RESULT_FIELDS = ("resultType", "ttlMs", "cacheScope")

# What a handshake-era result contains, exactly: a client of the older
# protocol validates against a schema that knows these keys and no others.
LEGACY_RESULT_KEYS = {
    "initialize": {"protocolVersion", "capabilities", "serverInfo", "instructions"},
    "tools/list": {"tools"},
    "tools/call": {"content", "structuredContent", "isError"},
    "ping": set(),
}
# How a patch that lost the race is allowed to fail: the context it was
# written against is gone, or the committer caught the file changing under it.
CONFLICT_ERROR_CODES = {
    "PATCH_CONTEXT_NOT_FOUND",
    "PATCH_CONTEXT_AMBIGUOUS",
    "PATCH_CONFLICT",
}
SDK_TIMEOUT_SECONDS = 60.0
STDIO_READ_TIMEOUT_SECONDS = 15.0
RACE_TIMEOUT_SECONDS = 60.0


def legacy_request(request_id: Any, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}}


def modern_request(request_id: Any, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    body = dict(params or {})
    body["_meta"] = {
        META_PROTOCOL_VERSION: MODERN_PROTOCOL_VERSION,
        META_CLIENT_CAPABILITIES: {},
    }
    return {"jsonrpc": "2.0", "id": request_id, "method": method, "params": body}


def modern_headers(request: dict[str, Any]) -> dict[str, str]:
    """The headers SEP-2243 has a modern request mirror its body with."""

    method = str(request["method"])
    headers = {"MCP-Protocol-Version": MODERN_PROTOCOL_VERSION, "Mcp-Method": method}
    name = request.get("params", {}).get("name")
    if method == "tools/call" and isinstance(name, str):
        headers["Mcp-Name"] = name
    return headers


def http_rpc(
    url: str,
    payload: dict[str, Any],
    *,
    headers: dict[str, str] | None = None,
    timeout: float = 20.0,
) -> tuple[int, dict[str, Any]]:
    """POST one JSON-RPC message and return the status with the raw envelope."""

    sent = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
    sent.update(headers or {"MCP-Protocol-Version": LEGACY_PROTOCOL_VERSION})
    request = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=sent, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return exc.code, json.loads(body) if body else {}


def modern_field_paths(node: Any, path: str = "response") -> list[str]:
    """Every place a modern-only key hides in a response, however deep."""

    found: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            here = f"{path}.{key}"
            if key in MODERN_RESULT_FIELDS or str(key).startswith(MODERN_META_PREFIX):
                found.append(here)
            found.extend(modern_field_paths(value, here))
    elif isinstance(node, list):
        for index, item in enumerate(node):
            found.extend(modern_field_paths(item, f"{path}[{index}]"))
    return found


def run_in_barrier(workers: dict[str, Callable[[], Any]], *, timeout: float = RACE_TIMEOUT_SECONDS) -> dict[str, Any]:
    """Run callables from a synchronized start and return what each produced.

    A barrier, not a stress loop: the window worth testing is the one where
    both threads are inside the same code at the same time, and a loop only
    finds it by accident.
    """

    barrier = threading.Barrier(len(workers), timeout=timeout)
    outcomes: dict[str, Any] = {}
    errors: dict[str, BaseException] = {}

    def run(tag: str, work: Callable[[], Any]) -> None:
        try:
            barrier.wait()
            outcomes[tag] = work()
        except BaseException as exc:  # noqa: BLE001 - reported on the test thread instead
            errors[tag] = exc

    threads = [threading.Thread(target=run, args=(tag, work), name=f"race-{tag}") for tag, work in workers.items()]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=timeout)
        if thread.is_alive():
            raise AssertionError(f"worker {thread.name} did not finish within {timeout}s")
    if errors:
        raise AssertionError(f"concurrent workers raised: {errors!r}")
    return outcomes


class StdioConnection:
    """A raw newline-delimited JSON-RPC pipe that performs no handshake of its own."""

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace
        self.process: subprocess.Popen[str] | None = None
        self.methods_sent: list[str] = []
        self._responses: queue.Queue[str] = queue.Queue()
        self._stderr: list[str] = []

    def __enter__(self) -> StdioConnection:
        self.process = subprocess.Popen(
            [sys.executable, "-m", "coding_tools_mcp", "--workspace", str(self.workspace), "--stdio"],
            cwd=str(self.workspace),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=prepend_repo_pythonpath(os.environ.copy()),
            text=True,
            start_new_session=True,
        )
        threading.Thread(target=self._drain_stdout, daemon=True).start()
        threading.Thread(target=self._drain_stderr, daemon=True).start()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        process = self.process
        if process is None:
            return
        if process.stdin is not None:
            try:
                process.stdin.close()
            except OSError:
                pass
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        for stream in (process.stdout, process.stderr):
            if stream is not None:
                stream.close()

    def _drain_stdout(self) -> None:
        process = self.process
        if process is None or process.stdout is None:
            return
        for line in process.stdout:
            self._responses.put(line)

    def _drain_stderr(self) -> None:
        process = self.process
        if process is None or process.stderr is None:
            return
        for line in process.stderr:
            self._stderr.append(line)

    def request(self, payload: dict[str, Any]) -> dict[str, Any]:
        process = self.process
        assert process is not None and process.stdin is not None
        self.methods_sent.append(str(payload.get("method")))
        process.stdin.write(json.dumps(payload, separators=(",", ":")) + "\n")
        process.stdin.flush()
        try:
            line = self._responses.get(timeout=STDIO_READ_TIMEOUT_SECONDS)
        except queue.Empty as exc:
            raise AssertionError(
                f"no stdio response for {payload.get('method')!r}; stderr={''.join(self._stderr)[-2000:]!r}"
            ) from exc
        return json.loads(line)


@contextmanager
def scratch_runtime(*, git: bool = True) -> Iterator[tuple[FixtureWorkspace, Runtime]]:
    """An in-process runtime over a throwaway copy of the fixture workspace."""

    with workspace_from_fixture("tiny-js-project", git=git) as workspace:
        runtime = Runtime(workspace.root)
        try:
            yield workspace, runtime
        finally:
            runtime.close()


def update_patch(path: str, old_line: str, new_line: str) -> str:
    return f"*** Begin Patch\n*** Update File: {path}\n@@\n-{old_line}\n+{new_line}\n*** End Patch\n"


class LegacyShapeTests(ComplianceTestCase):
    """A handshake-era client must not be able to tell that the new era exists."""

    def test_http_legacy_exchange_carries_no_modern_field(self) -> None:
        url = str(self.client.url)
        for method, params, expectation in legacy_script():
            with self.subTest(transport="http", method=method, expectation=expectation):
                status, response = http_rpc(url, legacy_request(1, method, params))
                self.assertEqual(status, 200, f"handshake-era responses stay 200: {response!r}")
                self.assert_legacy_envelope(method, response, expectation)

    def test_stdio_legacy_exchange_carries_no_modern_field(self) -> None:
        with StdioConnection(self.workspace.root) as connection:
            for method, params, expectation in legacy_script():
                with self.subTest(transport="stdio", method=method, expectation=expectation):
                    response = connection.request(legacy_request(1, method, params))
                    self.assert_legacy_envelope(method, response, expectation)

    def assert_legacy_envelope(self, method: str, response: dict[str, Any], expectation: str) -> None:
        self.assertEqual(response.get("jsonrpc"), "2.0", response)
        self.assertEqual(response.get("id"), 1, response)
        self.assertEqual(
            modern_field_paths(response),
            [],
            f"a handshake-era response must carry no modern field: {response!r}",
        )
        if expectation == "rpc_error":
            self.assertNotIn("result", response)
            self.assertEqual(response.get("error", {}).get("code"), -32601, response)
            return
        result = response.get("result")
        self.assertIsInstance(result, dict, response)
        self.assertEqual(set(result), LEGACY_RESULT_KEYS[method], f"{method} result keys drifted: {result!r}")
        if method == "initialize":
            self.assertEqual(result["protocolVersion"], LEGACY_PROTOCOL_VERSION)
        if method == "tools/call":
            self.assertEqual(result["isError"], expectation == "tool_error", result)


def legacy_script() -> list[tuple[str, dict[str, Any], str]]:
    """One pass over everything a handshake-era client actually sends."""

    return [
        (
            "initialize",
            {
                "protocolVersion": LEGACY_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "dual-era-legacy", "version": "1.0"},
            },
            "result",
        ),
        ("tools/list", {}, "result"),
        ("tools/call", {"name": "read_file", "arguments": {"path": "src/math.js"}}, "result"),
        ("tools/call", {"name": "read_file", "arguments": {"path": "no-such-file.txt"}}, "tool_error"),
        ("ping", {}, "result"),
        ("resources/read", {"uri": "file:///nope"}, "rpc_error"),
    ]


class ModernLifecycleTests(unittest.TestCase):
    """The new era from first byte to last: one process, no handshake in it."""

    def test_a_client_that_discovers_never_needs_to_initialize(self) -> None:
        with workspace_from_fixture("tiny-js-project", git=False) as workspace:
            with StdioConnection(workspace.root) as connection:
                discovered = connection.request(modern_request(1, "server/discover"))
                discovery = self.assert_modern_result(discovered)
                self.assertEqual(discovery.get("supportedVersions"), [MODERN_PROTOCOL_VERSION])
                self.assertEqual(discovery.get("capabilities"), {"tools": {"listChanged": False}})
                self.assertTrue(discovery.get("instructions"), discovery)
                self.assertEqual(discovery.get("ttlMs"), 0)
                self.assertEqual(discovery.get("cacheScope"), "private")

                listed = self.assert_modern_result(connection.request(modern_request(2, "tools/list")))
                self.assertTrue({tool["name"] for tool in listed["tools"]} >= {"read_file"})

                called = self.assert_modern_result(
                    connection.request(
                        modern_request(3, "tools/call", {"name": "read_file", "arguments": {"path": "src/math.js"}})
                    )
                )
                self.assertFalse(called.get("isError", False), called)
                self.assertEqual(structured_payload(called).get("path"), "src/math.js")

                self.assertNotIn("initialize", connection.methods_sent)

    def assert_modern_result(self, response: dict[str, Any]) -> dict[str, Any]:
        self.assertNotIn("error", response, response)
        result = response.get("result")
        self.assertIsInstance(result, dict, response)
        assert isinstance(result, dict)
        self.assertEqual(result.get("resultType"), "complete", result)
        self.assertEqual(
            result.get("_meta", {}).get(META_SERVER_INFO, {}).get("name"),
            "coding-tools-mcp",
            result,
        )
        return result


class ConcurrentClientTests(ComplianceTestCase):
    """Two clients, one server, one workspace: no crossed wires."""

    def test_two_http_clients_both_using_id_one_get_their_own_answer(self) -> None:
        url = str(self.client.url)
        for tag in ("alpha", "beta"):
            (self.workspace.root / f"{tag}.txt").write_text(f"{tag}-marker\n", encoding="utf-8")

        def read(path: str) -> tuple[int, dict[str, Any]]:
            return http_rpc(url, legacy_request(1, "tools/call", {"name": "read_file", "arguments": {"path": path}}))

        outcomes = run_in_barrier({tag: (lambda tag=tag: read(f"{tag}.txt")) for tag in ("alpha", "beta")})

        for tag in ("alpha", "beta"):
            with self.subTest(client=tag):
                status, response = outcomes[tag]
                self.assertEqual(status, 200)
                self.assertEqual(response.get("id"), 1)
                payload = structured_payload(response["result"])
                self.assertEqual(payload.get("path"), f"{tag}.txt", payload)
                self.assertIn(f"{tag}-marker", str(payload.get("content")))

    def test_a_legacy_and_a_modern_client_each_get_the_shape_they_asked_for(self) -> None:
        url = str(self.client.url)

        def legacy_list() -> tuple[int, dict[str, Any]]:
            return http_rpc(url, legacy_request(1, "tools/list"))

        def modern_list() -> tuple[int, dict[str, Any]]:
            request = modern_request(1, "tools/list")
            return http_rpc(url, request, headers=modern_headers(request))

        outcomes = run_in_barrier({"legacy": legacy_list, "modern": modern_list})

        legacy_status, legacy_response = outcomes["legacy"]
        self.assertEqual(legacy_status, 200)
        self.assertEqual(set(legacy_response["result"]), {"tools"})
        self.assertEqual(modern_field_paths(legacy_response), [], legacy_response)

        modern_status, modern_response = outcomes["modern"]
        self.assertEqual(modern_status, 200)
        modern_result = modern_response["result"]
        self.assertEqual(modern_result.get("resultType"), "complete", modern_result)
        self.assertEqual(modern_result.get("ttlMs"), 0)
        self.assertEqual(modern_result.get("cacheScope"), "private")
        self.assertEqual(
            [tool["name"] for tool in modern_result["tools"]],
            [tool["name"] for tool in legacy_response["result"]["tools"]],
            "both eras are served one catalog",
        )


class WorkspaceRaceTests(unittest.TestCase):
    """Deterministic races against the state one runtime shares between clients."""

    def test_two_patches_to_one_region_leave_a_whole_file_behind(self) -> None:
        old_line = "  return a - b;"
        replacements = {"alpha": "  return a + b;", "beta": "  return b - a;"}
        with scratch_runtime() as (workspace, runtime):
            target = workspace.root / "src" / "math.js"
            original = target.read_text(encoding="utf-8")
            self.assertIn(old_line, original)

            def patch(tag: str) -> dict[str, Any]:
                return runtime.call_tool(
                    "apply_patch", {"patch": update_patch("src/math.js", old_line, replacements[tag])}
                )

            outcomes = run_in_barrier({tag: (lambda tag=tag: patch(tag)) for tag in replacements})
            final = target.read_text(encoding="utf-8")

        winners = [tag for tag, result in outcomes.items() if not result.get("isError")]
        self.assertEqual(
            len(winners),
            1,
            f"two edits of one line cannot both apply, and neither may be lost: {outcomes!r}",
        )
        loser = next(tag for tag in replacements if tag not in winners)
        failure = structured_payload(outcomes[loser]).get("error", {})
        self.assertIn(failure.get("code"), CONFLICT_ERROR_CODES, outcomes[loser])
        self.assertEqual(
            final,
            original.replace(old_line, replacements[winners[0]]),
            "the file must be exactly what the winning patch produces",
        )

    def test_two_threads_racing_the_first_command_agree_on_the_runtime_tree(self) -> None:
        directory_keys = ("runtime_dir", "home", "tmpdir", "cache_dir")
        with scratch_runtime() as (_workspace, runtime):

            def first_command(tag: str) -> dict[str, Any]:
                started = runtime.call_tool(
                    "exec_command",
                    {"cmd": f"printf '{tag}'", "timeout_ms": 10000, "yield_time_ms": 5000},
                )
                environment = runtime.call_tool("check_exec_environment", {})
                return {"command": structured_payload(started), "environment": structured_payload(environment)}

            outcomes = run_in_barrier({tag: (lambda tag=tag: first_command(tag)) for tag in ("first", "second")})

            for tag, outcome in outcomes.items():
                with self.subTest(worker=tag):
                    self.assertEqual(outcome["command"].get("exit_code"), 0, outcome)
                    self.assertEqual(outcome["command"].get("stdout", tag), tag, outcome)
            directories = [{key: outcome["environment"][key] for key in directory_keys} for outcome in outcomes.values()]
            self.assertEqual(
                directories[0],
                directories[1],
                "the runtime tree must not move under a command that is already running",
            )
            self.assertEqual(
                directories[0],
                {
                    "runtime_dir": str(runtime.runtime_dir),
                    "home": str(runtime.home_dir),
                    "tmpdir": str(runtime.tmp_dir),
                    "cache_dir": str(runtime.cache_dir),
                },
            )

    def test_the_non_git_diff_fallback_survives_a_concurrent_patch(self) -> None:
        if shutil.which("git") is None:
            self.skipTest("git is not available")
        with scratch_runtime(git=False) as (_workspace, runtime):
            # The fallback diffs against the baselines apply_patch records, so
            # there has to be one before the race is worth running.
            seed = runtime.call_tool(
                "apply_patch", {"patch": update_patch("src/math.js", "  return a - b;", "  return a + b;")}
            )
            self.assertFalse(seed.get("isError"), seed)

            add = "*** Begin Patch\n*** Add File: notes/race.md\n+raced\n*** End Patch\n"
            outcomes = run_in_barrier(
                {
                    "patch": lambda: runtime.call_tool("apply_patch", {"patch": add}),
                    "diff": lambda: runtime.call_tool("git_diff", {}),
                }
            )

            self.assertFalse(outcomes["patch"].get("isError"), outcomes["patch"])
            diff_payload = structured_payload(outcomes["diff"])
            self.assertFalse(outcomes["diff"].get("isError"), diff_payload)
            self.assertIn("non-git diff fallback", diff_payload.get("warnings", []))
            self.assertIn("return a + b;", diff_payload.get("diff", ""))


def require_official_sdk(test: unittest.TestCase) -> None:
    """Load the official SDK, and refuse to let CI pass without it.

    This is the only check here that is not written against a client of our
    own, so a silent skip in CI would quietly remove the one independent
    reading of what this server does.
    """

    try:
        import mcp  # noqa: F401
    except ImportError as exc:
        message = (
            f"the official MCP python SDK is not importable ({exc}); "
            "install it with `pip install -e '.[dev]'`"
        )
        if os.environ.get("CI"):
            test.fail(f"CI must run the official SDK smoke: {message}")
        print(f"SKIP: {message}", file=sys.stderr, flush=True)
        test.skipTest(message)


async def sdk_smoke(transport: Any) -> dict[str, Any]:
    """Connect, negotiate, list the tools, and call one cheap read-only tool.

    The SDK probes `server/discover` before it considers a handshake, so what
    it reports back is also the verdict on that answer: a client we did not
    write read our discover result and settled on the era it describes.
    """

    from mcp import Client

    async with Client(transport, raise_exceptions=True) as client:
        listed = await client.list_tools()
        result = await client.call_tool("check_exec_environment", {})
        tools_capability = getattr(client.server_capabilities, "tools", None)
        return {
            "protocol_version": client.protocol_version,
            "server_name": getattr(client.server_info, "name", None),
            "instructions": client.instructions or "",
            "tools_capability": None if tools_capability is None else tools_capability.list_changed,
            "tools": sorted(tool.name for tool in listed.tools),
            "is_error": bool(result.is_error),
            "content": [type(item).__name__ for item in result.content],
        }


def run_sdk_smoke(transport: Any) -> dict[str, Any]:
    """Run one smoke exchange under a timeout, so a stall fails instead of hanging."""

    async def bounded() -> dict[str, Any]:
        return await asyncio.wait_for(sdk_smoke(transport), timeout=SDK_TIMEOUT_SECONDS)

    return asyncio.run(bounded())


def assert_sdk_smoke(test: unittest.TestCase, summary: dict[str, Any]) -> None:
    # Anything less than the modern version means the SDK read our discover
    # result and went back to the handshake anyway, which is the failure this
    # smoke exists to catch.
    test.assertEqual(summary["protocol_version"], MODERN_PROTOCOL_VERSION, summary)
    test.assertEqual(summary["server_name"], "coding-tools-mcp", summary)
    test.assertEqual(summary["tools_capability"], False, summary)
    test.assertIn("inside the configured workspace", summary["instructions"], summary)
    test.assertIn("check_exec_environment", summary["tools"])
    test.assertGreaterEqual(len(summary["tools"]), 18, summary)
    test.assertFalse(summary["is_error"], summary)
    test.assertTrue(summary["content"], summary)


class OfficialSDKStdioSmokeTests(unittest.TestCase):
    def test_the_official_sdk_can_drive_the_stdio_server(self) -> None:
        require_official_sdk(self)
        from mcp import StdioServerParameters
        from mcp.client.stdio import stdio_client

        with workspace_from_fixture("tiny-js-project", git=False) as workspace:
            parameters = StdioServerParameters(
                command=sys.executable,
                args=["-m", "coding_tools_mcp", "--workspace", str(workspace.root), "--stdio"],
                cwd=str(workspace.root),
                env=safe_server_env(),
            )
            summary = run_sdk_smoke(stdio_client(parameters))

        assert_sdk_smoke(self, summary)


class OfficialSDKHttpSmokeTests(ComplianceTestCase):
    def test_the_official_sdk_can_drive_the_http_server(self) -> None:
        require_official_sdk(self)
        assert_sdk_smoke(self, run_sdk_smoke(str(self.client.url)))


if __name__ == "__main__":
    unittest.main()
