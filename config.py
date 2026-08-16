"""CLI Module Configuration."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

__all__ = ["CliConfig"]


@dataclass
class CliConfig:
    """Конфигурация CLI-модуля.

    Приоритет конфигурации:
    1. Прямые аргументы (наивысший)
    2. Переменные окружения
    3. Дефолты
    """

    # Режим работы: "local" (прямой вызов provider) или "http" (REST)
    mode: str = "local"

    # HTTP режим: base URL REST API
    base_url: str = "http://localhost:8000/api/v1"

    # Таймаут запросов (секунды)
    timeout: float = 30.0

    # Файл для хранения токена
    token_file: str = "~/.mia/token"

    @classmethod
    def from_env(cls) -> CliConfig:
        """Создать конфигурацию из переменных окружения."""
        return cls(
            mode=os.getenv("MIA_CLI_MODE", "local"),
            base_url=os.getenv("MIA_CLI_BASE_URL", "http://localhost:8000/api/v1"),
            timeout=float(os.getenv("MIA_CLI_TIMEOUT", "30")),
            token_file=os.getenv("MIA_CLI_TOKEN_FILE", "~/.mia/token"),
        )
