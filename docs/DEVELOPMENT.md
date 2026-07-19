```markdown
# BackupHub. Development Guide

Документ предназначен для разработчиков: описывает, как поднять проект локально, устроен код и как запускать тесты.

---

## 1. Требования

- Docker Engine 24.x+
- Docker Compose (плагин или v2)
- Git

> **Важно:** Все команды выполняются из корня репозитория `backuphub/`.

---

## 2. Локальный запуск (Docker)

### 2.1. Быстрый старт

```bash
# 1. Клонирование репозитория
git clone <ссылка_на_репозиторий>
cd backuphub

# 2. Запуск dev-окружения
docker-compose -f local.docker-compose.yml up --build -d
```

Контейнеры:
- `bh_app_local` — Django-приложение (http://localhost:8000)
- `bh_celery_worker_local` — Celery worker
- `bh_celery_beat_local` — Celery Beat (планировщик)
- `bh_flower_local` — Flower (http://localhost:5555)
- `bh_postgres_local` — PostgreSQL (localhost:5432)
- `bh_redis` — Redis (localhost:6379)

### 2.2. Создание суперпользователя

```bash
docker-compose -f local.docker-compose.yml exec app python manage.py createsuperuser
```

### 2.3. Остановка и очистка

```bash
docker-compose -f local.docker-compose.yml down -v  # удалить тома
docker-compose -f local.docker-compose.yml down      # только остановить
```

---

## 3. Тестовое окружение (Docker)

```bash
# Запуск тестового стека (без runserver)
docker-compose -f test.docker-compose.yml up --build -d

# Выполнение тестов внутри контейнера
docker-compose -f test.docker-compose.yml exec app pytest -v
```

---

## 4. Структура проекта

```
backuphub/
├── app/                           # Django-приложение
│   ├── app/                       # Конфигурация Django (settings, urls, wsgi)
│   │   ├── settings.py            # Основные настройки, DRF, Celery
│   │   ├── urls.py                # Маршруты (UI + API)
│   │   ├── celery.py              # Celery-приложение
│   │   └── __init__.py
│   │
│   ├── api/                       # REST API (v1)
│   │   ├── v1/
│   │   │   └── backup_operations/   # ViewSet, serializers, filters, tests
│   │   ├── authentication.py        # X-API-Key аутентификация
│   │   ├── permissions.py           # HasValidApiKey, IsOwnerSystem
│   │   ├── throttling.py            # Rate limiting
│   │   ├── pagination.py            # Стандартная пагинация
│   │   └── exceptions.py            # Кастомный обработчик ошибок
│   │
│   ├── dictionaries/              # Справочники (SystemType, Environment, BackupTool, InformationSystem)
│   │   ├── models.py
│   │   ├── views.py               # CRUD для справочников
│   │   └── urls.py
│   │
│   ├── systems/                   # Целевые системы (TargetSystem, TargetSystemVersion)
│   │   ├── models.py              # API-ключ генерируется при создании
│   │   ├── views.py               # CRUD + history
│   │   └── urls.py
│   │
│   ├── configurations/            # Конфигурации бэкапов (BackupConfiguration, BackupConfigurationVersion)
│   │   ├── models.py
│   │   ├── views.py
│   │   └── urls.py
│   │
│   ├── operations/                # Факты выполнения бэкапов (BackupOperation)
│   │   ├── models.py              # Статусы: in_progress, success, error, warning, cancelled
│   │   ├── tasks.py               # send_backup_alert (Celery-задача)
│   │   ├── signals.py             # Триггер алерта при error/warning/cancelled
│   │   ├── apps.py                # ready() → импорт signals
│   │   └── urls.py
│   │
│   ├── templates/                 # Django-шаблоны
│   ├── static/                    # Статические файлы
│   ├── logs/                      # Лог-файлы (rotating)
│   ├── manage.py
│   ├── pytest.ini                 # Конфигурация pytest
│   └── conftest.py                # Фикстуры pytest
│
├── compose/
│   ├── local.Dockerfile           # Многоэтапный образ (builder + final)
│   ├── entrypoint                 # Ожидание PostgreSQL
│   ├── local.start                # runserver + миграции
│   └── celery/
│       ├── worker/local.start     # celery -A app worker
│       ├── beat/local.start       # celery -A app beat
│       └── flower/local.start     # celery -A app flower
│
├── local.docker-compose.yml         # Dev-стек
├── test.docker-compose.yml        # Тестовый стек
├── local.env                      # Переменные окружения (local)
├── local.requirements.txt         # Зависимости
└── requirements.txt               # Базовые зависимости
```

---

## 5. Схема данных (модели)

```
dictionaries/
├── SystemType          # Тип системы (PostgreSQL, GitLab, ...)
├── Environment         # Окружение (Production, Test, ...)
├── BackupTool          # Инструмент (pg_dump, Velero, ...)
└── InformationSystem   # Информационная система

systems/
├── TargetSystem        # Целевая система (имеет api_key)
│   └── TargetSystemVersion  # Версия системы (история изменений)

configurations/
├── BackupConfiguration       # Группа настроек
│   └── BackupConfigurationVersion  # Версия конфигурации (tool, mode, cron, storage)

operations/
└── BackupOperation           # Факт выполнения бэкапа
    # Связи:
    # - backup_configuration_version → BackupConfigurationVersion
    # - status ∈ {in_progress, success, error, warning, cancelled}
```

---

## 6. REST API (v1)

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/v1/backup-operations/` | Создать операцию (требуется `X-API-Key`) |
| GET | `/api/v1/backup-operations/` | Список операций |
| GET | `/api/v1/backup-operations/{id}/` | Детали операции |
| PATCH | `/api/v1/backup-operations/{id}/` | Обновить статус/результат |

Аутентификация: `X-API-Key: <uuid>` (ключ берётся из `TargetSystem.api_key`).

Документация:
- Swagger UI: http://localhost:8000/api/docs/
- ReDoc: http://localhost:8000/api/redoc/

---

## 7. Web UI (Django)

| Путь | Описание |
|------|----------|
| `/` | Дашборд (index) |
| `/target-systems/` | Список целевых систем |
| `/backup-configuration/` | Список конфигураций |
| `/backup-operations/` | Список операций |
| `/admin/` | Django-admin |

---

## 8. Тестирование

### 8.1. Запуск всех тестов

```bash
# В контейнере
docker-compose -f local.docker-compose.yml exec app pytest -v

# Локально (без Docker)
cd app && pytest -v
```

### 8.2. Покрытие кода

Порог: **70%** (см. `app/.coveragerc` и `app/pytest.ini`).

```bash
pytest --cov=app --cov-report=term-missing --cov-fail-under=70
```

### 8.3. Маркеры тестов

```ini
# pytest.ini
markers =
    slow: marks tests as slow
    integration: integration tests (require external services)
```

Запуск только быстрых тестов:

```bash
pytest -m "not slow and not integration"
```

### 8.4. Параллельный запуск

```bash
pytest -n auto
```

---

## 9. Линтинг

```bash
# Форматирование
black app/

# Проверка стиля
flake8 app/
ruff check app/
```

---

## 10. Полезные команды

```bash
# Миграции
docker-compose -f local.docker-compose.yml exec app python manage.py makemigrations
docker-compose -f local.docker-compose.yml exec app python manage.py migrate

# Shell в контейнер
docker-compose -f local.docker-compose.yml exec app python shell

# Просмотр логов
docker-compose -f local.docker-compose.yml logs -f app
docker-compose -f local.docker-compose.yml logs -f celery_worker
```

---

## 11. Где искать основную логику

| Функционал | Файлы |
|------------|-------|
| Маршруты UI | `app/app/urls.py` |
| Маршруты API | `app/api/v1/backup_operations/views.py` |
| Сериализация | `app/api/v1/backup_operations/serializers.py` |
| Аутентификация | `app/api/authentication.py` |
| Permissions | `app/api/permissions.py` |
| Celery-задачи | `app/operations/tasks.py` |
| Сигналы (алерты) | `app/operations/signals.py` |
| Модели | `app/*/models.py` |
| Формы | `app/*/forms.py` |
| Админка | `app/*/admin.py` |

---

## 12. Переменные окружения (local.env)

```ini
# Django
SECRET_KEY=...
DEBUG=1

# PostgreSQL
DB_HOST=postgres
DB_PORT=5432
POSTGRES_USER=postgres_user
POSTGRES_PASSWORD=posgres_password
POSTGRES_DB=postgres_db

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Flower
FLOWER_UNAUTHENTICATED_API=true
FLOWER_BASIC_AUTH=admin:admin

# STAGE
STAGE="local"
```

> **Внимание:** В production значения берутся из секретов Vault (см. `docs/SECURITY.md`).

---

## 13. Архитектурные ограничения

BackupHub **не выполняет** резервное копирование внешних систем. Он только:
- Принимает статусы через API;
- Хранит историю операций;
- Оркеструет расписание через Celery Beat;
- Отправляет алерты при ошибках.

Подробнее: `docs/ARCHITECTURE.md`.

---

## 14. CI/CD

См. `docs/DEPLOYMENT.md` — описаны workflow и процесс сборки production-образов.
```