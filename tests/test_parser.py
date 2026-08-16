"""Tests for CliParser — разбор аргументов, help, ошибки."""
from __future__ import annotations

import pytest

from cli.parser import CliParser, Command


class TestParserBasic:
    """Базовый разбор аргументов."""

    def test_parse_module_and_method(self, fake_registry):
        parser = CliParser(registry=fake_registry)
        cmd = parser.parse(["auth", "login"])
        assert cmd.module == "auth"
        assert cmd.method == "login"
        assert cmd.args == {}

    def test_parse_with_args(self, fake_registry):
        parser = CliParser(registry=fake_registry)
        cmd = parser.parse(["auth", "login", "--username", "admin", "--password", "secret"])
        assert cmd.module == "auth"
        assert cmd.method == "login"
        assert cmd.args["username"] == "admin"
        assert cmd.args["password"] == "secret"

    def test_parse_bool_flag_true(self, fake_registry):
        parser = CliParser(registry=fake_registry)
        cmd = parser.parse(["auth", "login", "--verbose"])
        assert cmd.args["verbose"] is True

    def test_parse_bool_explicit(self, fake_registry):
        parser = CliParser(registry=fake_registry)
        cmd = parser.parse(["auth", "login", "--flag", "true"])
        assert cmd.args["flag"] is True

    def test_parse_bool_false(self, fake_registry):
        parser = CliParser(registry=fake_registry)
        cmd = parser.parse(["auth", "login", "--flag", "false"])
        assert cmd.args["flag"] is False

    def test_parse_int_arg(self, fake_registry):
        parser = CliParser(registry=fake_registry)
        cmd = parser.parse(["auth", "list_users", "--offset", "10"])
        assert cmd.args["offset"] == 10

    def test_parse_float_arg(self, fake_registry):
        parser = CliParser(registry=fake_registry)
        cmd = parser.parse(["auth", "login", "--ratio", "3.14"])
        assert cmd.args["ratio"] == pytest.approx(3.14)


class TestParserTypeCoercion:
    """Приведение типов из метаданных."""

    def test_type_from_registry(self, fake_registry):
        """Тип берётся из MethodMeta.args."""
        parser = CliParser(registry=fake_registry)
        # list_users имеет offset: int, limit: int
        cmd = parser.parse(["auth", "list_users", "--offset", "5", "--limit", "10"])
        assert cmd.args["offset"] == 5
        assert cmd.args["limit"] == 10

    def test_type_unknown_defaults_to_str(self, fake_registry):
        parser = CliParser(registry=fake_registry)
        cmd = parser.parse(["auth", "login", "--unknown_arg", "hello"])
        assert cmd.args["unknown_arg"] == "hello"

    def test_int_parse_error(self, fake_registry):
        parser = CliParser(registry=fake_registry)
        with pytest.raises(SystemExit) as exc_info:
            parser.parse(["auth", "list_users", "--offset", "not_a_number"])
        assert exc_info.value.code == 2


class TestParserHelp:
    """Генерация help."""

    def test_help_exits_with_zero(self, fake_registry):
        parser = CliParser(registry=fake_registry)
        with pytest.raises(SystemExit) as exc_info:
            parser.parse(["--help"])
        assert exc_info.value.code == 0

    def test_module_help(self, fake_registry):
        parser = CliParser(registry=fake_registry)
        with pytest.raises(SystemExit) as exc_info:
            parser.parse(["auth", "--help"])
        assert exc_info.value.code == 0

    def test_method_help(self, fake_registry):
        parser = CliParser(registry=fake_registry)
        with pytest.raises(SystemExit) as exc_info:
            parser.parse(["auth", "login", "--help"])
        assert exc_info.value.code == 0

    def test_empty_args_shows_help(self, fake_registry):
        parser = CliParser(registry=fake_registry)
        with pytest.raises(SystemExit) as exc_info:
            parser.parse([])
        assert exc_info.value.code == 0


class TestParserErrors:
    """Ошибки парсинга."""

    def test_missing_method(self, fake_registry):
        parser = CliParser(registry=fake_registry)
        with pytest.raises(SystemExit) as exc_info:
            parser.parse(["auth"])
        assert exc_info.value.code == 2

    def test_unknown_flag(self, fake_registry):
        parser = CliParser(registry=fake_registry)
        with pytest.raises(SystemExit) as exc_info:
            parser.parse(["auth", "login", "positional_arg"])
        assert exc_info.value.code == 2

    def test_invalid_int_value(self, fake_registry):
        parser = CliParser(registry=fake_registry)
        with pytest.raises(SystemExit) as exc_info:
            parser.parse(["auth", "list_users", "--offset", "abc"])
        assert exc_info.value.code == 2
