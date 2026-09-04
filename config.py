"""CLI Module Configuration."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import ClassVar

from modules_system.pref_spec import PrefField

__all__ = ["CliConfig"]


@dataclass
class CliConfig:
    """Конфигурация CLI-модуля.

    Приоритет: аргументы > ENV > дефолты.
    Вызов только через ApiProxyProvider (local). HTTP/REST нет.
    """

    token_file: str = "~/.mia/token"

    SETTINGS: ClassVar[tuple[PrefField, ...]] = (
        PrefField(
            "token_file", "Token file",
            "Путь к файлу CLI-токена.",
            "string", "~/.mia/token", "Client", env="MIA_CLI_TOKEN_FILE",
            target="env", needs_restart=True,
        ),
    )

    @classmethod
    def from_env(cls) -> CliConfig:
        """Создать конфигурацию из переменных окружения."""
        return cls(
            token_file=os.getenv("MIA_CLI_TOKEN_FILE", "~/.mia/token"),
        )
