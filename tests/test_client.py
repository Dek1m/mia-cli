"""Tests for ApiClient — local вызов, token, ошибки."""
from __future__ import annotations

import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import patch

from cli.client import ApiClient, format_response
from cli.config import CliConfig


class TestApiClientLocal:
    """Тесты local режима (прямой вызов provider)."""

    def test_call_public_method(self, fake_proxy_provider):
        """Вызов публичного метода."""
        client = ApiClient(config=CliConfig(mode="local"), proxy_provider=fake_proxy_provider)
        result = asyncio.run(client.call("auth", "login", {"username": "admin", "password": "pass"}))
        assert result["error"] is None
        assert result["data"]["access_token"] == "fake-token"

    def test_call_without_provider(self):
        client = ApiClient(config=CliConfig(mode="local"), proxy_provider=None)
        result = asyncio.run(client.call("auth", "login", {"username": "admin"}))
        assert result["error"] is not None
        assert result["error"]["status_code"] == 503

    def test_call_method_not_found(self, fake_proxy_provider):
        client = ApiClient(config=CliConfig(mode="local"), proxy_provider=fake_proxy_provider)
        result = asyncio.run(client.call("auth", "nonexistent", {}))
        assert result["error"] is not None
        assert result["error"]["status_code"] == 404


class TestTokenStorage:
    """Тесты сохранения/загрузки токена."""

    def test_save_and_load_token(self, tmp_path):
        token_file = str(tmp_path / "token.json")
        config = CliConfig(token_file=token_file)
        client = ApiClient(config=config, proxy_provider=None)

        assert client.token is None

        client._save_token("test-access-token")
        assert client.token == "test-access-token"

        client2 = ApiClient(config=config, proxy_provider=None)
        assert client2.token == "test-access-token"

    def test_clear_token(self, tmp_path):
        token_file = str(tmp_path / "token.json")
        config = CliConfig(token_file=token_file)
        client = ApiClient(config=config, proxy_provider=None)
        client._save_token("test-token")
        client._clear_token()
        assert client.token is None

    def test_load_invalid_token_file(self, tmp_path):
        token_file = str(tmp_path / "token.json")
        Path(token_file).write_text("not json!!!", encoding="utf-8")
        config = CliConfig(token_file=token_file)
        client = ApiClient(config=config, proxy_provider=None)
        assert client.token is None

    def test_load_missing_token_file(self, tmp_path):
        config = CliConfig(token_file=str(tmp_path / "nonexistent.json"))
        client = ApiClient(config=config, proxy_provider=None)
        assert client.token is None


class TestFormatResponse:
    """Тесты форматирования ответа."""

    def test_format_success(self):
        result = {"data": {"id": "1", "name": "admin"}, "error": None}
        output = format_response(result)
        assert '"id": "1"' in output
        assert '"name": "admin"' in output

    def test_format_error(self):
        result = {"data": None, "error": {"code": "NOT_FOUND", "message": "not found", "status_code": 404}}
        output = format_response(result)
        assert "ОШИБКА [404]" in output
        assert "not found" in output

    def test_format_list_with_pagination(self):
        result = {
            "data": {
                "items": [{"id": "1"}, {"id": "2"}],
                "total": 10,
                "offset": 0,
                "limit": 2,
            },
            "error": None,
        }
        output = format_response(result)
        assert "Всего: 10" in output
        assert "показано 2" in output


class TestApiClientAuth:
    """Тесты авторизации в клиенте."""

    def test_token_sent_with_request(self, fake_proxy_provider, fake_auth_provider):
        """Токен передаётся в запросе — защищённый метод работает."""
        client = ApiClient(config=CliConfig(mode="local"), proxy_provider=fake_proxy_provider)
        # Регистрируем токен в fake auth provider
        fake_auth_provider.register_token("my-token", "user-1")
        client._save_token("my-token")
        result = asyncio.run(client.call("auth", "get_me", {}))
        assert result["error"] is None
        assert result["data"]["username"] == "admin"

    def test_401_triggers_login_prompt(self, fake_proxy_provider, fake_auth_provider):
        """При 401 клиент пытается предложить login (мокаем prompt)."""
        client = ApiClient(config=CliConfig(mode="local"), proxy_provider=fake_proxy_provider)
        # Мокаем _prompt_login чтобы он вернул токен и обновил self._token
        def mock_prompt():
            client._token = "new-login-token"
            fake_auth_provider.register_token("new-login-token", "user-1")
            return "new-login-token"

        client._prompt_login = mock_prompt
        result = asyncio.run(client.call("auth", "get_me", {}))
        assert result["error"] is None
        assert result["data"]["username"] == "admin"
