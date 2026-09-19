from __future__ import annotations

import argparse

from .paths import state_root
from .utf8 import configure_utf8_stdio


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="webgpt-codex")
    parser.add_argument("--version", action="store_true")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("paths")
    sub.add_parser("doctor")
    sub.add_parser("status")
    sub.add_parser("start")
    sub.add_parser("stop")
    sub.add_parser("restart")
    sub.add_parser("launcher")
    sub.add_parser("desktop-launcher")
    sub.add_parser("autostart")
    sub.add_parser("repair")
    sub.add_parser("manager")
    sub.add_parser("edge-runtime")
    sub.add_parser("deploy")
    sub.add_parser("bootstrap")
    sub.add_parser("add-mcp")
    sub.add_parser("loop")
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_utf8_stdio()
    parser = build_parser()
    args, unknown = parser.parse_known_args(argv)
    if args.version:
        from . import __version__
        print(__version__)
        return 0
    if args.command == "paths":
        print(state_root())
        return 0
    if args.command in {
        None,
        "doctor",
        "status",
        "start",
        "stop",
        "restart",
        "launcher",
        "desktop-launcher",
        "autostart",
        "repair",
        "manager",
        "edge-runtime",
        "deploy",
        "bootstrap",
        "add-mcp",
        "loop",
    }:
        from .commands import dispatch
        return dispatch(args.command or "status", unknown)
    parser.error("unknown command")
    return 2
