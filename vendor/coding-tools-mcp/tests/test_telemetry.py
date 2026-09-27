from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import time
import unittest
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import Mock, patch

from coding_tools_mcp import telemetry
from coding_tools_mcp.protocol import dispatch_rpc
from coding_tools_mcp.server import Runtime
from coding_tools_mcp.telemetry import ERROR_EVENTS_PER_SESSION, SessionTelemetry

_ENV_KEYS = ("CODING_TOOLS_MCP_TELEMETRY", "DO_NOT_TRACK", "CI")


@contextlib.contextmanager
def scrubbed_env(**overrides: str) -> Iterator[None]:
    """Run with the telemetry-controlling variables removed, then overridden.

    The ambient environment (CI sets ``CI=true``; sandboxes may set
    ``CODING_TOOLS_MCP_*``) must never decide what these tests observe.
    """

    with patch.dict(os.environ):
        for key in _ENV_KEYS:
            os.environ.pop(key, None)
        os.environ.update(overrides)
        yield


class _CapturingSender:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    def enqueue(self, events: list[dict[str, object]], *, wake: bool = False) -> None:
        self.events.extend(events)

    def flush(self) -> None:
        pass


LEGACY_PROTOCOL_VERSION = "2025-11-25"
MODERN_PROTOCOL_VERSION = "2026-07-28"
MODERN_META = {
    "io.modelcontextprotocol/protocolVersion": MODERN_PROTOCOL_VERSION,
    "io.modelcontextprotocol/clientCapabilities": {},
}


def _initialize(runtime: Runtime, client_name: str = "test-client") -> None:
    response = dispatch_rpc(
        runtime,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"clientInfo": {"name": client_name, "version": "9.9.9"}},
        },
    )
    assert response is not None and "error" not in response


def _modern_request(
    runtime: Runtime,
    method: str,
    params: dict[str, object] | None = None,
    *,
    client_info: dict[str, object] | None = None,
) -> dict[str, object] | None:
    """Dispatch one 2026-07-28 request, which states its version per request."""

    meta = dict(MODERN_META)
    if client_info is not None:
        meta["io.modelcontextprotocol/clientInfo"] = client_info
    body = dict(params or {})
    body["_meta"] = meta
    return dispatch_rpc(runtime, {"jsonrpc": "2.0", "id": 7, "method": method, "params": body})


def _events_by_name(sender: _CapturingSender) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for event in sender.events:
        grouped.setdefault(str(event["event"]), []).append(event)
    return grouped


def _properties(event: dict[str, object]) -> dict[str, object]:
    properties = event["properties"]
    assert isinstance(properties, dict)
    return properties


class TelemetryModeTests(unittest.TestCase):
    def test_default_is_on(self) -> None:
        with scrubbed_env():
            self.assertEqual(telemetry.telemetry_mode(), "on")

    def test_env_switch_disables(self) -> None:
        for value in ("off", "0", "false", "no", "disabled"):
            with self.subTest(value=value), scrubbed_env(CODING_TOOLS_MCP_TELEMETRY=value):
                self.assertEqual(telemetry.telemetry_mode(), "off")

    def test_do_not_track_disables(self) -> None:
        with scrubbed_env(DO_NOT_TRACK="1"):
            self.assertEqual(telemetry.telemetry_mode(), "off")

    def test_do_not_track_overrides_explicit_on(self) -> None:
        with scrubbed_env(CODING_TOOLS_MCP_TELEMETRY="on", DO_NOT_TRACK="1"):
            self.assertEqual(telemetry.telemetry_mode(), "off")

    def test_ci_disables(self) -> None:
        with scrubbed_env(CI="true"):
            self.assertEqual(telemetry.telemetry_mode(), "off")

    def test_debug_mode(self) -> None:
        with scrubbed_env(CODING_TOOLS_MCP_TELEMETRY="debug"):
            self.assertEqual(telemetry.telemetry_mode(), "debug")


class OffMeansOffTests(unittest.TestCase):
    def test_disabled_session_never_reaches_the_sender(self) -> None:
        for overrides in ({"CODING_TOOLS_MCP_TELEMETRY": "off"}, {"DO_NOT_TRACK": "1"}, {"CI": "1"}):
            with self.subTest(overrides=overrides), scrubbed_env(**overrides):
                get_sender = Mock()
                with patch.object(telemetry, "_get_sender", get_sender):
                    with tempfile.TemporaryDirectory() as tmp:
                        runtime = Runtime(Path(tmp))
                        _initialize(runtime)
                        runtime.call_tool("check_exec_environment", {})
                        runtime.call_tool("read_file", {"path": "missing.txt"})
                        runtime.close()
                get_sender.assert_not_called()

    def test_an_activating_request_writes_nothing_while_telemetry_is_off(self) -> None:
        """Off means no sender and no install id: building an event reads one."""

        saved_install_id = telemetry._install_id
        telemetry._install_id = None
        get_sender = Mock()
        try:
            with tempfile.TemporaryDirectory() as home:
                with scrubbed_env(CODING_TOOLS_MCP_TELEMETRY="off", HOME=home):
                    with patch.object(telemetry, "_get_sender", get_sender):
                        with tempfile.TemporaryDirectory() as tmp:
                            runtime = Runtime(Path(tmp))
                            dispatch_rpc(
                                runtime,
                                {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
                            )
                            runtime.close()
                get_sender.assert_not_called()
                self.assertFalse((Path(home) / ".coding-tools-mcp").exists(), "off must not create an install id")
        finally:
            telemetry._install_id = saved_install_id

    def test_post_sends_nothing_when_disabled(self) -> None:
        with scrubbed_env(CODING_TOOLS_MCP_TELEMETRY="off"):
            with patch.object(telemetry, "urlopen", Mock()) as opener:
                telemetry._post([{"event": "session_start"}])
            opener.assert_not_called()

    def test_debug_mode_prints_to_stderr_and_does_not_send(self) -> None:
        with scrubbed_env(CODING_TOOLS_MCP_TELEMETRY="debug"):
            stderr = io.StringIO()
            with patch.object(telemetry, "urlopen", Mock()) as opener:
                with contextlib.redirect_stderr(stderr):
                    telemetry._post([{"event": "session_start", "properties": {}}])
            opener.assert_not_called()
        output = stderr.getvalue()
        self.assertIn("telemetry (not sent):", output)
        self.assertIn("session_start", output)


def _run_probe_session() -> _CapturingSender:
    sender = _CapturingSender()
    with scrubbed_env(), patch.object(telemetry, "_get_sender", lambda: sender):
        with tempfile.TemporaryDirectory() as tmp:
            marker = "leakprobe-a8f3"
            workspace = Path(tmp) / marker
            workspace.mkdir()
            (workspace / f"{marker}.txt").write_text("leakprobe-content\n", encoding="utf-8")
            runtime = Runtime(workspace)
            _initialize(runtime, client_name="clientinfo-probe")
            runtime.call_tool("check_exec_environment", {})
            runtime.call_tool("read_file", {"path": f"{marker}-missing.txt"})
            runtime.call_tool("read_file", {"path": f"{marker}-missing.txt"})
            runtime.close()
    return sender


class SessionEventTests(unittest.TestCase):
    def test_payload_never_contains_paths_arguments_or_content(self) -> None:
        sender = _run_probe_session()
        serialized = json.dumps(sender.events)
        self.assertNotIn("leakprobe", serialized)
        self.assertNotIn("missing.txt", serialized)

    def test_session_events_carry_the_closed_schema(self) -> None:
        sender = _run_probe_session()
        by_name = _events_by_name(sender)
        self.assertEqual(len(by_name["session_start"]), 1)
        self.assertEqual(len(by_name["handshake"]), 1)
        self.assertEqual(len(by_name["session_end"]), 1)
        self.assertEqual(len(by_name["tool_error"]), 2)

        properties = _properties(by_name["session_start"][0])
        self.assertEqual(properties["$process_person_profile"], False)
        self.assertEqual(properties["transport"], "stdio")
        self.assertEqual(properties["permission_mode"], "safe")
        # One runtime serves every client of the workspace, so only the
        # handshake and the request that failed name a client at all.
        for event in sender.events:
            if event["event"] in {"handshake", "tool_error"}:
                continue
            with self.subTest(event=event["event"]):
                aggregate = _properties(event)
                for field in ("client_name", "client_version", "protocol_version"):
                    self.assertNotIn(field, aggregate)

        handshake = _properties(by_name["handshake"][0])
        self.assertEqual(handshake["client_name"], "clientinfo-probe")
        self.assertEqual(handshake["client_version"], "9.9.9")
        self.assertEqual(handshake["protocol_version"], LEGACY_PROTOCOL_VERSION)

        errors = by_name["tool_error"]
        first = _properties(errors[0])
        second = _properties(errors[1])
        self.assertEqual(first["tool"], "read_file")
        self.assertEqual(first["error_code"], "NOT_FOUND")
        self.assertEqual(first["consecutive_failures"], 1)
        self.assertEqual(second["consecutive_failures"], 2)
        # The failing calls were made straight against the runtime, so they
        # carry no request context and therefore no client identity.
        self.assertIsNone(first["client_name"])
        self.assertIsNone(first["client_version"])

        summaries = {str(_properties(event)["tool"]): _properties(event) for event in by_name["tool_summary"]}
        self.assertEqual(summaries["read_file"]["calls"], 2)
        self.assertEqual(summaries["read_file"]["ok"], 0)
        self.assertEqual(summaries["read_file"]["err_NOT_FOUND"], 2)
        self.assertEqual(summaries["check_exec_environment"]["calls"], 1)
        self.assertEqual(summaries["check_exec_environment"]["ok"], 1)
        self.assertNotIn("client_name", summaries["read_file"])

        end = _properties(by_name["session_end"][0])
        self.assertEqual(end["tool_calls"], 3)
        self.assertEqual(end["distinct_tools"], 2)
        self.assertEqual(end["errors_dropped"], 0)
        self.assertEqual(end["legacy_requests"], 1)
        self.assertEqual(end["modern_requests"], 0)
        self.assertEqual(end["discover_probes"], 0)
        for counter in ("evict_events", "evicted_bytes_total", "read_output_omitted_hits", "poll_omitted_hits"):
            self.assertEqual(end[counter], 0)

    def test_a_runtime_that_serves_no_request_emits_nothing(self) -> None:
        sender = _CapturingSender()
        with scrubbed_env(), patch.object(telemetry, "_get_sender", lambda: sender):
            with tempfile.TemporaryDirectory() as tmp:
                runtime = Runtime(Path(tmp))
                runtime.call_tool("check_exec_environment", {})
                runtime.call_tool("read_file", {"path": "missing.txt"})
                runtime.close()
        self.assertEqual(sender.events, [])

    def test_a_ping_only_runtime_emits_nothing(self) -> None:
        sender = _CapturingSender()
        with scrubbed_env(), patch.object(telemetry, "_get_sender", lambda: sender):
            with tempfile.TemporaryDirectory() as tmp:
                runtime = Runtime(Path(tmp))
                for request_id in (1, 2):
                    dispatch_rpc(runtime, {"jsonrpc": "2.0", "id": request_id, "method": "ping", "params": {}})
                _modern_request(runtime, "ping")
                runtime.close()
        self.assertEqual(sender.events, [], "an HTTP health probe must not create a session")

    def test_a_modern_client_that_never_handshakes_produces_a_session(self) -> None:
        sender = _CapturingSender()
        with scrubbed_env(), patch.object(telemetry, "_get_sender", lambda: sender):
            with tempfile.TemporaryDirectory() as tmp:
                runtime = Runtime(Path(tmp))
                # The very first request fails: activation happens before the
                # method runs, so its tool_error must not be lost.
                _modern_request(
                    runtime,
                    "tools/call",
                    {"name": "read_file", "arguments": {"path": "missing.txt"}},
                    client_info={"name": "modern-probe", "version": "2.0"},
                )
                _modern_request(runtime, "tools/list")
                runtime.close()

        by_name = _events_by_name(sender)
        self.assertEqual(len(by_name["session_start"]), 1)
        self.assertNotIn("handshake", by_name)
        self.assertEqual(len(by_name["tool_error"]), 1)
        error = _properties(by_name["tool_error"][0])
        self.assertEqual(error["tool"], "read_file")
        self.assertEqual(error["client_name"], "modern-probe")
        self.assertEqual(error["client_version"], "2.0")
        end = _properties(by_name["session_end"][0])
        self.assertEqual(end["modern_requests"], 2)
        self.assertEqual(end["legacy_requests"], 0)

    def test_discover_probes_are_counted_and_do_not_need_a_handshake(self) -> None:
        sender = _CapturingSender()
        with scrubbed_env(), patch.object(telemetry, "_get_sender", lambda: sender):
            with tempfile.TemporaryDirectory() as tmp:
                runtime = Runtime(Path(tmp))
                probe = dispatch_rpc(
                    runtime, {"jsonrpc": "2.0", "id": 1, "method": "server/discover", "params": {}}
                )
                assert probe is not None
                self.assertEqual(probe["error"]["code"], -32601)
                _initialize(runtime)
                runtime.close()

        by_name = _events_by_name(sender)
        self.assertEqual(len(by_name["session_start"]), 1)
        end = _properties(by_name["session_end"][0])
        self.assertEqual(end["discover_probes"], 1)
        self.assertEqual(end["legacy_requests"], 2)

    def test_self_reported_client_identity_is_sanitized(self) -> None:
        # A client names itself; the label is ours. Anything that would turn
        # one into free-form text, an address, or a path is dropped rather
        # than escaped, and a name is never long enough to be an identifier.
        cases = [
            (
                {
                    "name": "evil\r\nclient\u4e2d\x07" + "x" * 200,
                    "version": "1.0\n",
                    "secret": "must-not-travel",
                },
                "evilclient" + "x" * 30,
                "1.0",
            ),
            ({"name": "alice@example.com", "version": "2.0"}, "aliceexample.com", "2.0"),
            ({"name": "/home/alice/repo", "version": "3.0"}, "homealicerepo", "3.0"),
        ]
        for client_info, expected_name, expected_version in cases:
            with self.subTest(client_name=client_info["name"]):
                sender = _CapturingSender()
                with scrubbed_env(), patch.object(telemetry, "_get_sender", lambda: sender):
                    with tempfile.TemporaryDirectory() as tmp:
                        runtime = Runtime(Path(tmp))
                        _modern_request(
                            runtime,
                            "tools/call",
                            {"name": "read_file", "arguments": {"path": "missing.txt"}},
                            client_info=client_info,
                        )
                        runtime.close()

                serialized = json.dumps(sender.events)
                error = _properties(_events_by_name(sender)["tool_error"][0])
                self.assertEqual(error["client_name"], expected_name)
                self.assertEqual(error["client_version"], expected_version)
                self.assertNotIn("must-not-travel", serialized)
                for character in ("@", "/"):
                    self.assertNotIn(character, str(error["client_name"]))

    def test_every_handshake_is_recorded_but_the_session_starts_once(self) -> None:
        sender = _CapturingSender()
        with scrubbed_env(), patch.object(telemetry, "_get_sender", lambda: sender):
            with tempfile.TemporaryDirectory() as tmp:
                runtime = Runtime(Path(tmp))
                _initialize(runtime, client_name="first-connector")
                _initialize(runtime, client_name="second-connector")
                runtime.close()

        by_name = _events_by_name(sender)
        self.assertEqual(len(by_name["session_start"]), 1)
        self.assertEqual(
            [_properties(event)["client_name"] for event in by_name["handshake"]],
            ["first-connector", "second-connector"],
        )

    def test_output_retention_counters_travel_with_session_end(self) -> None:
        sender = _CapturingSender()
        with scrubbed_env(), patch.object(telemetry, "_get_sender", lambda: sender):
            with tempfile.TemporaryDirectory() as tmp:
                runtime = Runtime(Path(tmp))
                _initialize(runtime)
                runtime.command_manager.record_output_eviction("stdout", 512)
                runtime.command_manager.record_omitted_read("read_output")
                runtime.close()

        end = _properties(_events_by_name(sender)["session_end"][0])
        self.assertEqual(end["evict_events"], 1)
        self.assertEqual(end["evicted_bytes_total"], 512)
        self.assertEqual(end["read_output_omitted_hits"], 1)
        self.assertEqual(end["poll_omitted_hits"], 0)

    def test_error_events_are_capped_and_drops_are_counted(self) -> None:
        sender = _CapturingSender()
        with scrubbed_env(), patch.object(telemetry, "_get_sender", lambda: sender):
            session = SessionTelemetry(permission_mode="safe")
            session.record_request("legacy", "tools/call")
            for _ in range(ERROR_EVENTS_PER_SESSION + 5):
                session.record_tool_call(
                    "apply_patch", ok=False, error_code="PATCH_CONTEXT_MISMATCH", duration_ms=5, truncated=False
                )
            session.finish()
        errors = [event for event in sender.events if event["event"] == "tool_error"]
        self.assertEqual(len(errors), ERROR_EVENTS_PER_SESSION)
        end = next(event for event in sender.events if event["event"] == "session_end")
        properties = end["properties"]
        assert isinstance(properties, dict)
        self.assertEqual(properties["errors_dropped"], 5)

    def test_duration_buckets_and_finish_is_idempotent(self) -> None:
        sender = _CapturingSender()
        with scrubbed_env(), patch.object(telemetry, "_get_sender", lambda: sender):
            session = SessionTelemetry(permission_mode="safe")
            session.record_session_start(None, LEGACY_PROTOCOL_VERSION)
            for duration in (50, 500, 5_000, 50_000):
                session.record_tool_call("exec_command", ok=True, error_code=None, duration_ms=duration, truncated=True)
            session.finish()
            session.finish()
        summaries = [event for event in sender.events if event["event"] == "tool_summary"]
        self.assertEqual(len(summaries), 1)
        properties = summaries[0]["properties"]
        assert isinstance(properties, dict)
        for bucket in ("dur_lt_100ms", "dur_lt_1s", "dur_lt_10s", "dur_gte_10s"):
            self.assertEqual(properties[bucket], 1)
        self.assertEqual(properties["truncated"], 4)
        self.assertEqual(len([event for event in sender.events if event["event"] == "session_end"]), 1)


class FirstAppearanceLogTests(unittest.TestCase):
    """The one-line stderr notes an operator reads to see which era clients speak."""

    def setUp(self) -> None:
        self._saved = set(telemetry._first_seen)
        telemetry._first_seen.clear()

    def tearDown(self) -> None:
        telemetry._first_seen.clear()
        telemetry._first_seen.update(self._saved)

    def test_each_protocol_choice_is_logged_once_to_stderr(self) -> None:
        stderr = io.StringIO()
        # Logged for the operator, not for us: telemetry being off changes nothing.
        with scrubbed_env(CODING_TOOLS_MCP_TELEMETRY="off"), contextlib.redirect_stderr(stderr):
            with tempfile.TemporaryDirectory() as tmp:
                runtime = Runtime(Path(tmp))
                _initialize(runtime)
                _initialize(runtime)
                _modern_request(runtime, "tools/list")
                _modern_request(runtime, "ping")
                for request_id in (1, 2):
                    dispatch_rpc(
                        runtime,
                        {"jsonrpc": "2.0", "id": request_id, "method": "server/discover", "params": {}},
                    )
                runtime.close()

        lines = [line for line in stderr.getvalue().splitlines() if line.startswith("coding-tools-mcp:")]
        self.assertEqual(
            lines,
            [
                f"coding-tools-mcp: legacy client handshake ({LEGACY_PROTOCOL_VERSION})",
                "coding-tools-mcp: modern client request (tools/list)",
                "coding-tools-mcp: server/discover probe",
            ],
        )

    def test_a_method_name_cannot_write_a_second_line_into_the_log(self) -> None:
        """The method comes off the wire, and the note is one line about it."""

        stderr = io.StringIO()
        method = "tools/list\r\ncoding-tools-mcp: forged operator note\x07"
        with scrubbed_env(CODING_TOOLS_MCP_TELEMETRY="off"), contextlib.redirect_stderr(stderr):
            with tempfile.TemporaryDirectory() as tmp:
                runtime = Runtime(Path(tmp))
                _modern_request(runtime, method)
                runtime.close()

        output = stderr.getvalue()
        lines = [line for line in output.splitlines() if line.startswith("coding-tools-mcp:")]
        self.assertEqual(
            lines,
            ["coding-tools-mcp: modern client request (tools/listcoding-tools-mcpforgedoperatornote)"],
            output,
        )
        self.assertNotIn("forged operator note", output)
        self.assertNotIn("\x07", output)


class FailureStreakKeyingTests(unittest.TestCase):
    """D2: streaks belong to a (tool, error_code) pair, not to one global slot."""

    def session(self) -> SessionTelemetry:
        return SessionTelemetry(permission_mode="safe")

    def fail(self, session: SessionTelemetry, tool: str, code: str) -> None:
        session.record_tool_call(tool, ok=False, error_code=code, duration_ms=1, truncated=False)

    def succeed(self, session: SessionTelemetry, tool: str, outcome: str | None = None) -> None:
        session.record_tool_call(
            tool, ok=True, error_code=None, duration_ms=1, truncated=False, outcome=outcome
        )

    def test_another_tools_success_does_not_clear_a_streak(self) -> None:
        session = self.session()
        self.fail(session, "apply_patch", "PATCH_CONTEXT_NOT_FOUND")
        self.fail(session, "apply_patch", "PATCH_CONTEXT_NOT_FOUND")
        self.succeed(session, "read_file")
        self.fail(session, "apply_patch", "PATCH_CONTEXT_NOT_FOUND")
        self.assertEqual(session.consecutive_failures("apply_patch", "PATCH_CONTEXT_NOT_FOUND"), 3)

    def test_two_error_codes_on_one_tool_count_separately(self) -> None:
        session = self.session()
        self.fail(session, "apply_patch", "PATCH_CONTEXT_NOT_FOUND")
        self.fail(session, "apply_patch", "PATCH_CONFLICT")
        self.assertEqual(session.consecutive_failures("apply_patch", "PATCH_CONTEXT_NOT_FOUND"), 1)
        self.assertEqual(session.consecutive_failures("apply_patch", "PATCH_CONFLICT"), 1)

    def test_a_success_of_the_same_tool_clears_its_streaks(self) -> None:
        session = self.session()
        self.fail(session, "apply_patch", "PATCH_CONTEXT_NOT_FOUND")
        self.succeed(session, "apply_patch")
        self.assertEqual(session.consecutive_failures("apply_patch", "PATCH_CONTEXT_NOT_FOUND"), 0)

    def test_a_failed_operation_is_not_a_success_and_clears_nothing(self) -> None:
        session = self.session()
        self.fail(session, "exec_command", "INVALID_ARGUMENT")
        self.succeed(session, "exec_command", outcome="exited_nonzero")
        self.assertEqual(session.consecutive_failures("exec_command", "INVALID_ARGUMENT"), 1)
        self.succeed(session, "exec_command", outcome="exited_0")
        self.assertEqual(session.consecutive_failures("exec_command", "INVALID_ARGUMENT"), 0)


class OperationOutcomeTests(unittest.TestCase):
    """D1: a command that exits non-zero is not a successful operation."""

    def test_tool_summary_separates_call_success_from_operation_success(self) -> None:
        sender = _CapturingSender()
        with scrubbed_env(CODING_TOOLS_MCP_TELEMETRY="on"), patch.object(
            telemetry, "_get_sender", return_value=sender
        ):
            session = SessionTelemetry(permission_mode="safe")
            session.record_request(LEGACY_PROTOCOL_VERSION, "tools/call")
            for outcome in ("exited_0", "exited_nonzero", "timeout", "signal"):
                session.record_tool_call(
                    "exec_command",
                    ok=True,
                    error_code=None,
                    duration_ms=1,
                    truncated=False,
                    outcome=outcome,
                )
            session.finish()
        summary = next(
            _properties(event)
            for event in sender.events
            if event["event"] == "tool_summary" and _properties(event)["tool"] == "exec_command"
        )
        self.assertEqual(summary["calls"], 4)
        self.assertEqual(summary["ok"], 1)
        self.assertEqual(summary["operation_failures"], 3)
        self.assertEqual(summary["outcome_exited_nonzero"], 1)
        self.assertEqual(summary["outcome_timeout"], 1)
        self.assertEqual(summary["outcome_signal"], 1)

    def test_spawn_error_is_not_counted_as_two_failures(self) -> None:
        sender = _CapturingSender()
        with scrubbed_env(CODING_TOOLS_MCP_TELEMETRY="on"), patch.object(
            telemetry, "_get_sender", return_value=sender
        ):
            session = SessionTelemetry(permission_mode="safe")
            session.record_request(LEGACY_PROTOCOL_VERSION, "tools/call")
            session.record_tool_call(
                "exec_command",
                ok=False,
                error_code="COMMAND_SPAWN_FAILED",
                duration_ms=1,
                truncated=False,
                outcome="spawn_error",
            )
            session.finish()
        summary = next(
            _properties(event)
            for event in sender.events
            if event["event"] == "tool_summary" and _properties(event)["tool"] == "exec_command"
        )
        self.assertEqual(summary["calls"], 1)
        self.assertEqual(summary["ok"], 0)
        self.assertEqual(summary["errors"], 1)
        self.assertEqual(summary["operation_failures"], 0)
        self.assertEqual(summary["outcome_spawn_error"], 1)

    def test_a_nonzero_exit_is_reported_as_the_operation_outcome(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Runtime(Path(tmp), permission_mode="safe")
            try:
                payload = runtime.exec_command({"cmd": "exit 3", "timeout_ms": 5000})
            finally:
                runtime.close()
        self.assertIs(payload["ok"], True)
        self.assertEqual(payload["exit_code"], 3)
        self.assertEqual(payload["operation_outcome"], "exited_nonzero")

    def test_a_poll_observed_failure_is_attributed_to_exec_command(self) -> None:
        # Every poll of a finished command reports the same terminal outcome.
        # Counting each one turned a single failing build into as many failed
        # operations as the model happened to poll.
        sender = _CapturingSender()
        with scrubbed_env(CODING_TOOLS_MCP_TELEMETRY="on"), patch.object(
            telemetry, "_get_sender", return_value=sender
        ), tempfile.TemporaryDirectory() as tmp:
            runtime = Runtime(Path(tmp), permission_mode="trusted")
            try:
                runtime.telemetry.record_request(LEGACY_PROTOCOL_VERSION, "tools/call")
                command = (
                    f'"{sys.executable}" -c "import sys,time; '
                    'time.sleep(0.2); sys.exit(7)"'
                )
                started = runtime.call_tool(
                    "exec_command",
                    {"cmd": command, "yield_time_ms": 1, "timeout_ms": 5000},
                )
                command_id = started["structuredContent"]["command_id"]
                self.assertEqual(started["structuredContent"]["operation_outcome"], "running")
                poll_calls = 0
                for _ in range(20):
                    polled = runtime.call_tool(
                        "write_stdin",
                        {"command_id": command_id, "chars": "", "yield_time_ms": 250},
                    )
                    poll_calls += 1
                    if polled["structuredContent"]["operation_outcome"] != "running":
                        break
                # The poll still tells the truth about the command…
                self.assertEqual(polled["structuredContent"]["operation_outcome"], "exited_nonzero")
                repeated = runtime.call_tool("write_stdin", {"command_id": command_id, "chars": ""})
                poll_calls += 1
                self.assertEqual(repeated["structuredContent"]["operation_outcome"], "exited_nonzero")
            finally:
                runtime.close()
        summaries = {
            _properties(event)["tool"]: _properties(event)
            for event in sender.events
            if event["event"] == "tool_summary"
        }
        # … but the failed operation is counted once, by the call that ran it.
        self.assertEqual(summaries["exec_command"]["outcome_exited_nonzero"], 1)
        self.assertEqual(summaries["exec_command"]["operation_failures"], 1)
        self.assertNotIn("outcome_exited_nonzero", summaries["write_stdin"])
        self.assertEqual(summaries["write_stdin"]["operation_failures"], 0)
        self.assertEqual(summaries["write_stdin"]["calls"], poll_calls)
        self.assertEqual(summaries["write_stdin"]["ok"], poll_calls)

    def test_every_terminal_observer_attributes_the_outcome_to_exec_command(self) -> None:
        for observer in ("write_stdin", "read_output", "kill_command"):
            with self.subTest(observer=observer), scrubbed_env(
                CODING_TOOLS_MCP_TELEMETRY="on"
            ), patch.object(telemetry, "_get_sender", return_value=(sender := _CapturingSender())):
                with tempfile.TemporaryDirectory() as tmp:
                    runtime = Runtime(Path(tmp), permission_mode="safe")
                    runtime.telemetry.record_request(LEGACY_PROTOCOL_VERSION, "tools/call")
                    started_at = time.time()
                    runtime.emit_tool_trace(
                        "exec_command",
                        {},
                        {"ok": True, "command_id": "background", "operation_outcome": "running"},
                        started_at,
                    )
                    runtime.emit_tool_trace(
                        observer,
                        {},
                        {
                            "ok": True,
                            "command_id": "background",
                            "operation_outcome": "exited_nonzero",
                        },
                        started_at,
                    )
                    runtime.close()

                summaries = {
                    _properties(event)["tool"]: _properties(event)
                    for event in sender.events
                    if event["event"] == "tool_summary"
                }
                self.assertEqual(summaries["exec_command"]["calls"], 1)
                self.assertEqual(summaries["exec_command"]["ok"], 0)
                self.assertEqual(summaries["exec_command"]["operation_failures"], 1)
                self.assertEqual(summaries["exec_command"]["outcome_exited_nonzero"], 1)
                self.assertEqual(summaries[observer]["calls"], 1)
                self.assertEqual(summaries[observer]["ok"], 1)
                self.assertEqual(summaries[observer]["operation_failures"], 0)
                self.assertNotIn("outcome_exited_nonzero", summaries[observer])


class DocumentationDriftTests(unittest.TestCase):
    def test_documented_schema_matches_emitted_events(self) -> None:
        doc = (Path(__file__).resolve().parents[1] / "docs" / "telemetry.md").read_text(encoding="utf-8")
        emitted = {str(event["event"]) for event in _run_probe_session().events}
        self.assertEqual(emitted, {"session_start", "handshake", "tool_error", "tool_summary", "session_end"})
        for name in emitted:
            self.assertIn(f"`{name}`", doc)
        self.assertIn(f"max {ERROR_EVENTS_PER_SESSION} per session", doc)


class InstallIdTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = telemetry._install_id
        telemetry._install_id = None

    def tearDown(self) -> None:
        telemetry._install_id = self._saved

    def test_install_id_is_random_stable_and_resettable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"HOME": tmp}):
                first = telemetry.install_id()
                self.assertEqual(telemetry.install_id(), first)
                path = Path(tmp) / ".coding-tools-mcp" / "id"
                self.assertEqual(path.read_text(encoding="utf-8").strip(), first)
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
                self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)

                telemetry._install_id = None
                path.unlink()
                second = telemetry.install_id()
                self.assertNotEqual(second, first)
                self.assertEqual(len(second), 32)


if __name__ == "__main__":
    unittest.main()
