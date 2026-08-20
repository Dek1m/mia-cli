"""CLI Module Configuration."""
from __future__ import annotations

import os
from dataclasses import dataclass

__all__ = ["CliConfig"]


@dataclass
class CliConfig:
    """Конфигурация CLI-модуля.

    Приоритет: аргументы > ENV > дефолты.
    Вызов только через ApiProxyProvider (local). HTTP/REST нет.
    """

    token_file: str = "~/.mia/token"

    @classmethod
    def from_env(cls) -> CliConfig:
        """Создать конфигурацию из переменных окружения."""
        return cls(
            token_file=os.getenv("MIA_CLI_TOKEN_FILE", "~/.mia/token"),
        )
