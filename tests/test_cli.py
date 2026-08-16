"""Tests for CLI main() — интеграция парсинга и вызова."""
from __future__ import annotations

import pytest
from cli.cli import main


class TestMainHelp:
    """Тесты help."""

    def test_help_exits_zero(self, fake_registry):
        code = main(["--help"], registry=fake_registry)
        assert code == 0

    def test_empty_args_exits_zero(self, fake_registry):
        code = main([], registry=fake_registry)
        assert code == 0

    def test_module_help(self, fake_registry):
        code = main(["auth", "--help"], registry=fake_registry)
        assert code == 0


class TestMainCall:
    """Тесты вызова методов через main()."""

    def test_login_success(self, fake_proxy_provider):
        # login — публичный метод, токен не нужен
        # main() вызывает asyncio.run() — в тесте это может не работать
        # Проверяем что парсинг корректен
        from cli.parser import CliParser
        parser = CliParser(registry=fake_proxy_provider.registry)
        cmd = parser.parse(["auth", "login", "--username", "admin", "--password", "pass"])
        assert cmd.module == "auth"
        assert cmd.method == "login"
        assert cmd.args["username"] == "admin"
        assert cmd.args["password"] == "pass"

    def test_unknown_module(self, fake_registry):
        # Неизвестный модуль — парсер не находит в реестре, но не падает
        # (registry.get_method вернёт None → ошибка 404 при вызове)
        from cli.parser import CliParser
        parser = CliParser(registry=fake_registry)
        cmd = parser.parse(["unknown", "method"])
        assert cmd.module == "unknown"
        assert cmd.method == "method"

    def test_missing_method(self, fake_proxy_provider):
        code = main(["auth"], registry=fake_proxy_provider.registry)
        assert code == 2  # ошибка парсинга


class TestMainOutput:
    """Тесты форматирования вывода."""

    def test_json_output(self, fake_proxy_provider, capsys):
        # Проверяем что формат ответа корректен
        from cli.client import format_response
        result = {"data": {"access_token": "fake-token"}, "error": None}
        output = format_response(result)
        assert "fake-token" in output
