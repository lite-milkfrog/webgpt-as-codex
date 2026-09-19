from __future__ import annotations


def dispatch(command: str, argv: list[str]) -> int:
    if command == "doctor":
        from .doctor import cli_doctor
        return cli_doctor(argv)
    if command == "status":
        from .runtime import cli_status
        return cli_status(argv)
    if command == "start":
        from .runtime import cli_start
        return cli_start(argv)
    if command == "stop":
        from .runtime import cli_stop
        return cli_stop(argv)
    if command == "repair":
        from .repair import cli_repair
        return cli_repair(argv)
    if command == "manager":
        from .manager import cli_manager
        return cli_manager(argv)
    if command == "bootstrap":
        from .bootstrap import cli_bootstrap
        return cli_bootstrap(argv)
    if command == "add-mcp":
        from .registry import cli_add_mcp
        return cli_add_mcp(argv)
    raise ValueError(command)
