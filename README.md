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

## Режимы работы

- **local** (по умолчанию): прямой вызов через ApiProxyProvider
- **http**: HTTP запросы к REST API (будущая Фаза 3b)

## Конфигурация

| Переменная | Дефолт | Описание |
|---|---|---|
| `MIA_CLI_MODE` | `local` | Режим работы (local/http) |
| `MIA_CLI_BASE_URL` | `http://localhost:8000/api/v1` | Base URL REST API |
| `MIA_CLI_TIMEOUT` | `30` | Таймаут запросов (сек) |
| `MIA_CLI_TOKEN_FILE` | `~/.mia/token` | Файл токена |

## Exit codes

- `0` — успех
- `1` — ошибка выполнения
- `2` — ошибка парсинга аргументов
