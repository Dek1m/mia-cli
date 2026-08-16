"""ApiClient — вызов API-методов через apiproxy.

Два режима:
- local: прямой вызов ApiProxyProvider.call (по умолчанию)
- http: HTTP запросы к REST API (для будущей Фазы 3b)

Токен хранится в файле (~/.mia/token).
"""
from __future__ import annotations

import getpass
import json
import sys
from pathlib import Path
from typing import Any

from argenta_logging import get_logger

from .config import CliConfig

log = get_logger(__name__)

__all__ = ["ApiClient"]


class ApiClient:
    """Клиент для вызова API-методов."""

    def __init__(
        self,
        config: CliConfig,
        proxy_provider: Any | None = None,
    ) -> None:
        self._config = config
        self._proxy_provider = proxy_provider
        self._token: str | None = None
        self._load_token()

    @property
    def token(self) -> str | None:
        return self._token

    def _token_path(self) -> Path:
        """Путь к файлу токена."""
        return Path(self._config.token_file).expanduser()

    def _load_token(self) -> None:
        """Загрузить токен из файла."""
        token_path = self._token_path()
        if token_path.exists():
            try:
                data = json.loads(token_path.read_text(encoding="utf-8"))
                self._token = data.get("access_token")
            except (json.JSONDecodeError, OSError):
                self._token = None

    def _save_token(self, token: str) -> None:
        """Сохранить токен в файл."""
        token_path = self._token_path()
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(
            json.dumps({"access_token": token}, indent=2) + "\n",
            encoding="utf-8",
        )
        self._token = token
        log.info("token_saved", path=str(token_path))

    def _clear_token(self) -> None:
        """Удалить токен."""
        token_path = self._token_path()
        if token_path.exists():
            token_path.unlink()
        self._token = None

    def _prompt_login(self) -> str | None:
        """Запросить логин/пароль у пользователя.

        Returns:
            Access token или None при ошибке.
        """
        print("Требуется авторизация", file=sys.stderr)
        username = input("Username: ").strip()
        if not username:
            return None
        password = getpass.getpass("Password: ")
        if not password:
            return None

        # Вызываем auth.login
        kwargs = {"username": username, "password": password}
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    result = pool.submit(asyncio.run, self._call_local("auth", "login", kwargs)).result()
            else:
                result = loop.run_until_complete(self._call_local("auth", "login", kwargs))
        except RuntimeError:
            import asyncio as _aio
            result = _aio.run(self._call_local("auth", "login", kwargs))

        if result.get("error"):
            print(f"Ошибка авторизации: {result['error']['message']}", file=sys.stderr)
            return None

        data = result.get("data", {})
        access_token = data.get("access_token")
        if access_token:
            self._save_token(access_token)
        return access_token

    async def call(
        self,
        module: str,
        method: str,
        kwargs: dict[str, Any],
    ) -> dict[str, Any]:
        """Вызвать API-метод.

        При 401 — автоматически предлагает login.
        """
        result = await self._call_with_retry(module, method, kwargs)

        # Обработка 401 — повторный запрос с login
        error = result.get("error")
        if error and error.get("status_code") == 401:
            print("Токен недействителен или отсутствует", file=sys.stderr)
            new_token = self._prompt_login()
            if new_token:
                result = await self._call_local(module, method, kwargs)

        return result

    async def _call_with_retry(
        self,
        module: str,
        method: str,
        kwargs: dict[str, Any],
    ) -> dict[str, Any]:
        """Вызов с автоматическим обновлением токена."""
        if self._config.mode == "http":
            return await self._call_http(module, method, kwargs)
        return await self._call_local(module, method, kwargs)

    async def _call_local(
        self,
        module: str,
        method: str,
        kwargs: dict[str, Any],
    ) -> dict[str, Any]:
        """Прямой вызов через ApiProxyProvider."""
        if self._proxy_provider is None:
            return {
                "data": None,
                "error": {
                    "code": "SERVICE_UNAVAILABLE",
                    "message": "ApiProxyProvider недоступен",
                    "status_code": 503,
                },
            }

        return await self._proxy_provider.call(
            module_name=module,
            method_name=method,
            kwargs=kwargs,
            token=self._token,
        )

    async def _call_http(
        self,
        module: str,
        method: str,
        kwargs: dict[str, Any],
    ) -> dict[str, Any]:
        """HTTP запрос к REST API (для будущей Фазы 3b)."""
        try:
            import httpx
        except ImportError:
            return {
                "data": None,
                "error": {
                    "code": "DEPENDENCY_MISSING",
                    "message": "httpx не установлен. Используйте режим 'local' или установите httpx.",
                    "status_code": 500,
                },
            }

        url = f"{self._config.base_url}/{module}/{method}"
        headers = {}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        try:
            async with httpx.AsyncClient(timeout=self._config.timeout) as client:
                response = await client.post(url, json=kwargs, headers=headers)
                return response.json()
        except httpx.TimeoutException:
            return {
                "data": None,
                "error": {
                    "code": "TIMEOUT",
                    "message": f"Таймаут запроса ({self._config.timeout}с)",
                    "status_code": 408,
                },
            }
        except httpx.RequestError as e:
            return {
                "data": None,
                "error": {
                    "code": "NETWORK_ERROR",
                    "message": f"Ошибка сети: {e}",
                    "status_code": 502,
                },
            }


def format_response(result: dict[str, Any], output_format: str = "json") -> str:
    """Форматировать ответ для вывода.

    Args:
        result: Ответ API {data, error}.
        output_format: Формат вывода ("json" или "text").

    Returns:
        Отформатированная строка.
    """
    if result.get("error"):
        error = result["error"]
        return f"ОШИБКА [{error.get('status_code', '?')}]: {error.get('message', 'Неизвестная ошибка')}"

    data = result.get("data")

    # Пагинация: если ответ содержит items/total/offset/limit
    if isinstance(data, dict) and "items" in data:
        items = data["items"]
        total = data.get("total", len(items))
        offset = data.get("offset", 0)
        limit = data.get("limit", 100)
        result_str = json.dumps(items, indent=2, ensure_ascii=False, default=str)
        return f"{result_str}\n\n--- Всего: {total} (показано {len(items)}, смещение {offset}, лимит {limit}) ---"

    return json.dumps(data, indent=2, ensure_ascii=False, default=str)
