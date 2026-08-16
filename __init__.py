"""CLI Module — командная строка для вызова функций через apiproxy.

Формат: mia {module} {method} [--arg value ...]

Использование:
    mia auth login --username admin --password ***
    mia auth list_users
    mia --help
    mia auth --help
    mia auth login --help
"""
from __future__ import annotations

from typing import Any

from modules_system.module_base import ModuleBase

# Relative imports с fallback для pytest
try:
    from .config import CliConfig
    from .parser import CliParser, Command
    from .client import ApiClient
except ImportError:
    import importlib
    import sys
    from pathlib import Path as _Path

    _pkg_dir = _Path(__file__).resolve().parent
    _parent = "cli"

    def _lazy_import(module_name: str):
        full = f"{_parent}.{module_name}"
        if full not in sys.modules:
            spec = importlib.util.spec_from_file_location(
                full, _pkg_dir / f"{module_name}.py",
            )
            mod = importlib.util.module_from_spec(spec)
            mod.__package__ = _parent
            sys.modules[full] = mod
            spec.loader.exec_module(mod)
        return sys.modules[full]

    CliConfig = _lazy_import("config").CliConfig  # type: ignore[assignment]
    CliParser = _lazy_import("parser").CliParser  # type: ignore[assignment]
    Command = _lazy_import("parser").Command  # type: ignore[assignment]
    ApiClient = _lazy_import("client").ApiClient  # type: ignore[assignment]

__all__ = [
    "CliModule",
    "CliConfig",
    "CliParser",
    "Command",
    "ApiClient",
]

from argenta_logging import get_logger

log = get_logger(__name__)

MODULE_VERSION = "1.0.0"


class CliModule(ModuleBase):
    """CLI-модуль для Mia Framework.

    Предоставляет:
    - Разбор аргументов командной строки
    - Вызов методов через apiproxy (local или http режим)
    - Автогенерацию help из реестра методов
    """

    @property
    def name(self) -> str:
        return "cli"

    @property
    def version(self) -> str:
        return MODULE_VERSION

    def __init__(self, config: CliConfig | None = None) -> None:
        self._config = config or CliConfig.from_env()
        self._parser: CliParser | None = None
        self._client: ApiClient | None = None

    def on_load(self, state: Any) -> None:
        """Инициализация модуля."""
        # Получаем ApiProxyProvider из DI (если доступен)
        proxy_provider = None
        try:
            from modules.apiproxy.provider import ApiProxyProvider
            proxy_provider = state.services.resolve(ApiProxyProvider)
        except Exception:
            log.warning("ApiProxyProvider not found in DI — CLI будет работать в HTTP режиме")

        # Создаём парсер и клиент
        self._parser = CliParser(registry=proxy_provider.registry if proxy_provider else None)
        self._client = ApiClient(
            config=self._config,
            proxy_provider=proxy_provider,
        )

        log.info(
            "cli_module_loaded",
            version=self.version,
            mode=self._config.mode,
        )

    def on_unload(self) -> None:
        self._parser = None
        self._client = None
        log.info("cli_module_unloaded")
