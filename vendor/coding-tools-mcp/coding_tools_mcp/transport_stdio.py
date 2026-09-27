from __future__ import annotations

import json
import sys
from typing import Any, Protocol, TextIO

from .protocol import (
    RequestContext,
    dispatch_rpc,
    invalid_request_response,
    jsonrpc_error,
    response_id,
)
from .telemetry import SessionTelemetry


class StdioRuntime(Protocol):
    telemetry: SessionTelemetry

    def initialize(
        self,
        client_info: dict[str, Any] | None = None,
        protocol_version: str = ...,
    ) -> dict[str, Any]: ...

    def initialize_result(self, protocol_version: str = ...) -> dict[str, Any]: ...

    def discover_payload(self) -> dict[str, Any]: ...

    def server_identity(self) -> dict[str, Any]: ...

    def list_tools(self) -> dict[str, Any]: ...

    def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        *,
        context: RequestContext | None = None,
    ) -> dict[str, Any]: ...

    def close(self) -> None: ...


def serve_stdio(
    runtime: StdioRuntime,
    *,
    input_stream: TextIO | None = None,
    output_stream: TextIO | None = None,
) -> int:
    source = input_stream or sys.stdin
    sink = output_stream or sys.stdout
    try:
        for line in source:
            if not line.strip():
                continue
            try:
                request = json.loads(line)
            except (json.JSONDecodeError, RecursionError):
                # RecursionError included: a deeply nested document is a
                # document this server cannot parse, not a reason to end the
                # session.
                response = jsonrpc_error(None, -32700, "Parse error")
            else:
                try:
                    response = (
                        dispatch_rpc(runtime, request)
                        if isinstance(request, dict)
                        else invalid_request_response()
                    )
                except Exception as exc:  # noqa: BLE001 - keep the stdio server alive
                    if isinstance(request, dict) and "id" not in request:
                        # A notification is answered with nothing, however
                        # badly its handling went.
                        continue
                    response = jsonrpc_error(
                        response_id(request) if isinstance(request, dict) else None,
                        -32603,
                        str(exc),
                    )
            if response is not None:
                sink.write(
                    json.dumps(response, separators=(",", ":")) + "\n"
                )
                sink.flush()
    finally:
        runtime.close()
    return 0
