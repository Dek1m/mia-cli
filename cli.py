"""CLI — точка входа для командной строки mia.

main(argv) — парсинг → help или вызов → печать.
Может быть вызван из Python или как CLI команда.

Exit codes: 0 — успех, 1 — ошибка, 2 — ошибка парсинга.
"""
from __future__ import annotations

import asyncio
import sys
from typing import Any

from .config import CliConfig
from .parser import CliParser
from .client import ApiClient, format_response

__all__ = ["main"]


def main(argv: list[str] | None = None, registry: Any | None = None, log: Any | None = None) -> int:
    """Точка входа CLI.

    Args:
        argv: Аргументы командной строки (по умолчанию sys.argv[1:]).
        registry: MethodRegistry для help и валидации (опционально).
        log: Log facade (optional).

    Returns:
        Код возврата: 0 — успех, 1 — ошибка, 2 — ошибка парсинга.
    """
    if argv is None:
        argv = sys.argv[1:]

    config = CliConfig.from_env()
    parser = CliParser(registry=registry, log=log)
    client = ApiClient(config=config, log=log)

    # Парсинг (parser.parse может бросить SystemExit для help)
    try:
        command = parser.parse(argv)
    except SystemExit as e:
        return e.code

    # Вызов метода
    try:
        result = asyncio.run(
            client.call(command.module, command.method, command.args)
        )
    except Exception as e:
        if log is not None:
            log.error(
                "cli_call_error",
                extra={
                    "module": command.module,
                    "method": command.method,
                    "error_type": type(e).__name__,
                    "error": str(e),
                },
            )
        print(f"ОШИБКА: {e}", file=sys.stderr)
        return 1

    # Печать результата
    output = format_response(result)
    print(output)

    # Код возврата
    if result.get("error"):
        return 1
    return 0
