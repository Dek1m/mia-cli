# cli

CLI для Mia Framework — вызов API-методов из командной строки.

## Формат

```
mia {module} {method} [--arg value ...]
```

## Примеры

```bash
# Вход в систему
mia auth login --username admin --password mypass

# Список пользователей
mia auth list_users

# Создание пользователя
mia auth create_user --username newuser --password Secure123

# Справка
mia --help
mia auth --help
mia auth login --help
```

Вызов идёт напрямую через ApiProxyProvider. HTTP-транспорта нет.

## Конфигурация

| Переменная | Дефолт | Описание |
|---|---|---|
| `MIA_CLI_TOKEN_FILE` | `~/.mia/token` | Файл токена |

## Exit codes

- `0` — успех
- `1` — ошибка выполнения
- `2` — ошибка парсинга аргументов
