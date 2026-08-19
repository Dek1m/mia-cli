"""CliParser — разбор аргументов командной строки.

Формат: mia {module} {method} [--arg value ...]
Поддержка: --help на всех уровнях, типизация аргументов, secret-поля через getpass.
"""
from __future__ import annotations

import getpass
import sys
from dataclasses import dataclass, field
from typing import Any

__all__ = ["CliParser", "Command"]


@dataclass
class Command:
    """Разобранный запрос CLI."""
    module: str
    method: str
    args: dict[str, Any] = field(default_factory=dict)


class CliParser:
    """Парсер CLI-аргументов.

    Использует метаданные MethodRegistry для:
    - Автогенерации help
    - Типизации аргументов
    - Определения secret-полей
    """

    def __init__(self, registry: Any | None = None, log: Any | None = None) -> None:
        self._registry = registry
        self._log = log

    def parse(self, argv: list[str]) -> Command:
        """Разобрать аргументы командной строки.

        Формат: mia [module] [method] [--arg value ...]

        Args:
            argv: Аргументы (без program name, т.е. sys.argv[1:]).

        Returns:
            Command с module, method и args.

        Raises:
            SystemExit: При ошибках парсинга (код 2).
        """
        if not argv:
            self._print_general_help()
            raise SystemExit(0)

        # Проверяем --help на верхнем уровне
        if argv[0] in ("--help", "-h"):
            if len(argv) == 1:
                self._print_general_help()
            elif len(argv) == 2:
                self._print_module_help(argv[1])
            elif len(argv) == 3:
                self._print_method_help(argv[1], argv[2])
            else:
                self._print_general_help()
            raise SystemExit(0)

        # module и method обязательны
        if len(argv) < 2:
            print("Ошибка: укажите module и method", file=sys.stderr)
            print("Формат: mia {module} {method} [--arg value ...]", file=sys.stderr)
            raise SystemExit(2)

        module = argv[0]
        method = argv[1]

        # Проверяем --help для module (mia auth --help)
        if method in ("--help", "-h"):
            self._print_module_help(module)
            raise SystemExit(0)

        # Проверяем --help для method
        if len(argv) > 2 and argv[2] in ("--help", "-h"):
            self._print_method_help(module, method)
            raise SystemExit(0)

        # Парсим оставшиеся аргументы
        raw_args = argv[2:]
        args = self._parse_args(raw_args, module, method)

        return Command(module=module, method=method, args=args)

    def _parse_args(
        self,
        raw_args: list[str],
        module: str,
        method: str,
    ) -> dict[str, Any]:
        """Разобрать --key value аргументы.

        Args:
            raw_args: Сырые аргументы (после module method).
            module: Имя модуля (для help).
            method: Имя метода (для help).

        Returns:
            Словарь {key: value} с приведёнными типами.
        """
        args: dict[str, Any] = {}
        i = 0
        while i < len(raw_args):
            arg = raw_args[i]
            if not arg.startswith("--"):
                print(f"Ошибка: неизвестный аргумент '{arg}' (ожидается --key)", file=sys.stderr)
                raise SystemExit(2)

            key = arg[2:]  # убираем --

            # Проверяем, есть ли значение
            if i + 1 < len(raw_args) and not raw_args[i + 1].startswith("--"):
                value_str = raw_args[i + 1]
                i += 2
            else:
                # --flag без значения → bool True
                value_str = "true"
                i += 1

            # Определяем тип из метаданных реестра
            expected_type = self._get_arg_type(module, method, key)
            args[key] = self._coerce(value_str, expected_type, key)

        return args

    def _get_arg_type(self, module: str, method: str, arg_name: str) -> str:
        """Получить ожидаемый тип аргумента из реестра.

        Args:
            module: Имя модуля.
            method: Имя метода.
            arg_name: Имя аргумента.

        Returns:
            Строка типа (str, int, float, bool).
        """
        if self._registry is None:
            return "str"

        meta = self._registry.get_method(module, method)
        if meta is None:
            return "str"

        return meta.args.get(arg_name, "str")

    def _coerce(self, value_str: str, expected_type: str, key: str) -> Any:
        """Привести строковое значение к нужному типу.

        Авто-определение: если registry не знает тип, определяем
        по значению: true/false/1/0 → bool, число → int/float.

        Args:
            value_str: Строковое значение.
            expected_type: Ожидаемый тип.
            key: Имя аргумента (для secret-поля).

        Returns:
            Приведённое значение.
        """
        if expected_type == "bool":
            return value_str.lower() in ("true", "1", "yes")
        elif expected_type == "int":
            try:
                return int(value_str)
            except ValueError:
                print(f"Ошибка: аргумент '{key}' должен быть int, получено '{value_str}'", file=sys.stderr)
                raise SystemExit(2)
        elif expected_type == "float":
            try:
                return float(value_str)
            except ValueError:
                print(f"Ошибка: аргумент '{key}' должен быть float, получено '{value_str}'", file=sys.stderr)
                raise SystemExit(2)
        else:
            # str — авто-определение для удобства CLI
            low = value_str.lower()
            if low in ("true", "yes"):
                return True
            if low in ("false", "no"):
                return False
            try:
                return int(value_str)
            except ValueError:
                pass
            try:
                return float(value_str)
            except ValueError:
                pass
            return value_str

    def _print_general_help(self) -> None:
        """Вывести общую справку."""
        print("mia — CLI для Mia Framework")
        print()
        print("Использование:")
        print("  mia {module} {method} [--arg value ...]")
        print()
        if self._registry:
            modules = self._registry.list_modules()
            if modules:
                print("Доступные модули:")
                for mod in modules:
                    methods = self._registry.list_methods(mod)
                    descriptions = [m.description for m in methods[:3]]
                    desc_str = ", ".join(descriptions) if descriptions else "нет методов"
                    print(f"  {mod:15s} {desc_str}")
                print()
                print("Подробнее: mia {module} --help")
            else:
                print("Нет зарегистрированных модулей")
        else:
            print("Реестр методов недоступен")
        print()
        print("Примеры:")
        print("  mia auth login --username admin --password mypass")
        print("  mia auth list_users")
        print("  mia auth --help")

    def _print_module_help(self, module: str) -> None:
        """Вывести справку по модулю."""
        if self._registry is None:
            print(f"Реестр методов недоступен — невозможно показать help для '{module}'")
            return

        methods = self._registry.list_methods(module)
        if not methods:
            print(f"Модуль '{module}' не найден или не имеет методов")
            return

        print(f"Модуль: {module}")
        print()
        for m in methods:
            args_str = ", ".join(f"{k}: {v}" for k, v in m.args.items()) if m.args else "нет аргументов"
            print(f"  {m.name:25s} {m.description}")
            print(f"    Аргументы: {args_str}")
            print()

    def _print_method_help(self, module: str, method: str) -> None:
        """Вывести справку по методу."""
        if self._registry is None:
            print(f"Реестр методов недоступен — невозможно показать help для '{module}.{method}'")
            return

        meta = self._registry.get_method(module, method)
        if meta is None:
            print(f"Метод '{module}.{method}' не найден")
            return

        print(f"Метод: {module}.{method}")
        print(f"Описание: {meta.description}")
        print()
        if meta.args:
            print("Аргументы:")
            for arg_name, arg_type in meta.args.items():
                print(f"  --{arg_name:20s} ({arg_type})")
        else:
            print("Аргументов нет")
        print()
        print(f"Тип возврата: {meta.return_type or 'не указан'}")
        print(f"Публичный: {'да' if meta.public else 'нет'}")
        if meta.required_permission:
            print(f"Требуемое разрешение: {meta.required_permission}")
