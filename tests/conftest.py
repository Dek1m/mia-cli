"""Conftest для CLI тестов — динамическая загрузка модуля cli."""
from __future__ import annotations

import importlib
import importlib.util
import sys
import types
from pathlib import Path
from typing import Any

import pytest

# ── Динамическая загрузка модуля cli ──────────────────

_MODULE_DIR = Path(__file__).resolve().parent.parent

_fake_package = types.ModuleType("cli")
_fake_package.__path__ = [str(_MODULE_DIR)]  # type: ignore[attr-defined]
_fake_package.__package__ = "cli"
sys.modules["cli"] = _fake_package


def _load_submodule(name: str) -> types.ModuleType:
    """Загрузить подмодуль из cli директории."""
    file_path = _MODULE_DIR / f"{name}.py"
    if not file_path.exists():
        raise FileNotFoundError(f"Module file not found: {file_path}")

    full_name = f"cli.{name}"
    spec = importlib.util.spec_from_file_location(
        full_name, file_path,
        submodule_search_locations=[],
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot create spec for {full_name}")

    module = importlib.util.module_from_spec(spec)
    module.__package__ = "cli"
    sys.modules[full_name] = module
    spec.loader.exec_module(module)
    return module


# Загружаем модули в правильном порядке зависимостей
_config = _load_submodule("config")
_parser = _load_submodule("parser")
_client = _load_submodule("client")
_cli = _load_submodule("cli")

# Экспортируем
from cli.config import CliConfig  # noqa: E402
from cli.parser import CliParser, Command  # noqa: E402
from cli.client import ApiClient, format_response  # noqa: E402
from cli.cli import main  # noqa: E402

# ── Загрузка apiproxy для фейкового registry ────────────

_APIPROXY_DIR = Path(__file__).resolve().parent.parent.parent / "apiproxy"
_fake_apiproxy = types.ModuleType("apiproxy")
_fake_apiproxy.__path__ = [str(_APIPROXY_DIR)]  # type: ignore[attr-defined]
_fake_apiproxy.__package__ = "apiproxy"
sys.modules["apiproxy"] = _fake_apiproxy


def _load_apiproxy_submodule(name: str) -> types.ModuleType:
    file_path = _APIPROXY_DIR / f"{name}.py"
    if not file_path.exists():
        raise FileNotFoundError(f"Module file not found: {file_path}")
    full_name = f"apiproxy.{name}"
    spec = importlib.util.spec_from_file_location(
        full_name, file_path,
        submodule_search_locations=[],
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot create spec for {full_name}")
    module = importlib.util.module_from_spec(spec)
    module.__package__ = "apiproxy"
    sys.modules[full_name] = module
    spec.loader.exec_module(module)
    return module


_load_apiproxy_submodule("config")
_load_apiproxy_submodule("registry")
_load_apiproxy_submodule("middleware")
_load_apiproxy_submodule("converter")
_load_apiproxy_submodule("provider")

from apiproxy.registry import MethodRegistry, MethodMeta  # noqa: E402
from apiproxy.provider import ApiProxyProvider  # noqa: E402
from apiproxy.config import ApiproxyConfig  # noqa: E402
from apiproxy.middleware import AuthMiddleware  # noqa: E402


# ── Фейковый AuthProvider ──────────────────────────────


class FakeAuthProvider:
    """Фейковый auth_provider для тестов."""

    def __init__(self) -> None:
        self._tokens: dict[str, str] = {}  # token → user_id

    def register_token(self, token: str, user_id: str) -> None:
        self._tokens[token] = user_id

    async def validate_token(self, access_token: str) -> Any:
        user_id = self._tokens.get(access_token)
        if user_id is None:
            return None

        class _UserCtx:
            def __init__(self, uid: str) -> None:
                self.user_id = uid
                self.username = "testuser"
                self.perms_version = 1

        return _UserCtx(user_id)

    async def check_permission(self, user_id: str, permission: str) -> bool:
        return True


# ── Фикстуры ────────────────────────────────────────────


@pytest.fixture
def fake_registry() -> MethodRegistry:
    """Фейковый registry с методами auth модуля."""
    registry = MethodRegistry()

    async def _login(username: str = "", password: str = "") -> dict[str, Any]:
        return {"access_token": "fake-token", "user_id": "user-1"}

    async def _list_users(offset: int = 0, limit: int = 100) -> list[dict[str, Any]]:
        return [{"id": "user-1", "username": "admin"}]

    async def _create_user(username: str = "", password: str = "") -> dict[str, Any]:
        return {"id": "new-user", "username": username}

    async def _get_me() -> dict[str, Any]:
        return {"id": "user-1", "username": "admin"}

    registry.register("auth", "login", {
        "name": "login",
        "description": "Вход в систему",
        "args": {"username": "str", "password": "str"},
        "return_type": "dict",
        "public": True,
        "required_permission": None,
    }, _login)

    registry.register("auth", "list_users", {
        "name": "list_users",
        "description": "Список пользователей",
        "args": {"offset": "int", "limit": "int"},
        "return_type": "list",
        "public": False,
        "required_permission": "users:list",
    }, _list_users)

    registry.register("auth", "create_user", {
        "name": "create_user",
        "description": "Создать пользователя",
        "args": {"username": "str", "password": "str"},
        "return_type": "dict",
        "public": False,
        "required_permission": "users:create",
    }, _create_user)

    registry.register("auth", "get_me", {
        "name": "get_me",
        "description": "Получить данные текущего пользователя",
        "args": {},
        "return_type": "dict",
        "public": False,
        "required_permission": "users:read",
    }, _get_me)

    return registry


@pytest.fixture
def fake_auth_provider() -> FakeAuthProvider:
    return FakeAuthProvider()


@pytest.fixture
def fake_proxy_provider(fake_registry: MethodRegistry, fake_auth_provider: FakeAuthProvider) -> ApiProxyProvider:
    """Фейковый ApiProxyProvider с тем же registry что и fake_registry."""
    config = ApiproxyConfig(whitelist=["auth"])
    provider = ApiProxyProvider(config=config, auth_provider=fake_auth_provider)
    # Заменяем registry на тот, что уже заполнен методами
    provider._registry = fake_registry
    return provider
