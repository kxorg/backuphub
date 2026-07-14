# BackupHub

1. О проекте

BackupHub — система централизованного управления и мониторинга резервного копирования. Предназначена для операторов и интеграторов, которым нужно собирать факты выполнения бэкапов, версионировать конфигурации и предоставлять внешним системам удобный API для отправки статусов и результатов.

2. Стек

| Компонент | Версия | Роль |
|---|---:|---|
| Django | 5.2 | Веб-фреймворк, ORM, админка (файл: app/app/settings.py)
| Django REST Framework (DRF) | (см. requirements.txt) | REST API v1 (app/api)
| Celery | 5.4 | Фоновые задачи (compose/ — старт скрипты)
| Redis | 8.8 | Брокер и backend для Celery
| PostgreSQL | 16 | Основная БД
| Flower | 2.0 | Мониторинг Celery (http://localhost:5555)
| Docker Compose | — | Локальная и деплой конфигурация (local.docker-compose.yml, deploy.docker-compose.yml)

3. Быстрый старт

Короткие, рабочие шаги (локально):

1) Сборка и запуск:

   docker compose -f local.docker-compose.yml up -d --build

2) Проверить доступное UI и сервисы:

- http://localhost:8000 — UI
- http://localhost:8000/admin/ — админка
- http://localhost:8000/api/docs/ — Swagger UI (drf-spectacular)
- http://localhost:5555 — Flower (учёт: admin:admin, берётся из local.env)

4. Структура папок (основное)

- app/ — основной код проекта
  - app/ — Django project (settings, urls, wsgi, celery)
  - api/ — внешние API (версия v1 лежит в app/api/v1/backup_operations)
  - systems/ — TargetSystem, TargetSystemVersion (app/systems/models.py)
  - configurations/ — BackupConfiguration, BackupConfigurationVersion (app/configurations/models.py)
  - operations/ — BackupOperation (app/operations/models.py)
  - dictionaries/ — справочники: SystemType, Environment, BackupTool (app/dictionaries/models.py)
  - templates/, static/ — frontend шаблоны и статические файлы
- compose/ — Dockerfile и запускающие скрипты (/start, /entrypoint)
- local.docker-compose.yml — конфигурация для локальной разработки (использует local.env)
- deploy.docker-compose.yml — конфигурация для деплоя (использует ./.env)
- .github/workflows/ — CI/CD (pr_tests.yml, deploy_dev.yml, telegram_notify.yml)

5. Модели данных (кратко, 8 моделей и связи)

1) SystemType (app/dictionaries/models.py) — справочник типа системы (FK в TargetSystem).
2) Environment (app/dictionaries/models.py) — окружение (dev/stage/prod) (FK в TargetSystem).
3) BackupTool (app/dictionaries/models.py) — справочник инструментов бэкапа (FK в BackupConfigurationVersion).
4) TargetSystem (app/systems/models.py) — целевая система; содержит api_key (UUID, автоматически генерируется) для внешней аутентификации; связь 1→N с TargetSystemVersion.
   - api_key: в модели (default=uuid.uuid4, editable=False, unique=True) — см. app/systems/models.py (строки около определения api_key).
5) TargetSystemVersion (app/systems/models.py) — версии TargetSystem (версионирование): fields: version_number, is_current, valid_from, valid_to; связана с TargetSystem (FK).
6) BackupConfiguration (app/configurations/models.py) — логическая конфигурация бэкапа; ссылается на TargetSystemVersion через target_system_version (FK).
7) BackupConfigurationVersion (app/configurations/models.py) — версии конфигурации (backup_tool, version_number, is_current, valid_from/valid_to и параметры: rpo/rto, retention и т.д.); связана с BackupConfiguration (FK).
8) BackupOperation (app/operations/models.py) — запись факта выполнения бэкапа; ссылается на BackupConfigurationVersion (FK backup_configuration_version). Хранит: status, started_at, finished_at, size_bytes, storage_path, error_message, metadata.

Принцип версионирования

- TargetSystem → TargetSystemVersion (история изменений целевой системы).
- BackupConfiguration → BackupConfigurationVersion (история и параметры конкретной конфигурации).

Значение is_current и valid_from/valid_to

- is_current (в версиях) помечает активную (рабочую) версию, которую следует использовать при создании новых операций.
- valid_from/valid_to задают период валидности версии — дают возможность хранить историю и выбирать версию по дате.

6. Внешний API (v1)

- Base URL: /api/v1/
- Аутентификация: HTTP-заголовок X-API-Key со значением UUID (TargetSystem.api_key). Реализация: app/api/authentication.py (ApiKeyAuthentication). Пример заголовка: X-API-Key: 01234567-89ab-cdef-0123-456789abcdef

Эндпоинты (основные, версия v1)

- POST /api/v1/backup-operations/ — создать операцию (обязательное поле: backup_configuration_id). Сериализатор: app/api/v1/backup_operations/serializers.py -> BackupOperationCreateSerializer
- GET /api/v1/backup-operations/ — список (фильтры: status, hostname, backup_configuration_id, started_after, started_before). Фильтры реализованы в app/api/v1/backup_operations/filters.py
- GET /api/v1/backup-operations/{id}/ — детали (чтение через BackupOperationReadSerializer)
- PATCH /api/v1/backup-operations/{id}/ — обновление статуса/результатов (BackupOperationUpdateSerializer)

Маппинг статусов (API ↔ DB):
- RUNNING → in_progress
- SUCCESS → success
- FAILED → error
(Источник: app/api/utils/status_mapping.py)

Формат ошибок:

{ "error": { "code": ..., "message": "...", "details": ... } }

7. Переменные окружения (из local.env)

| Переменная | Назначение | Пример |
|---|---|---|
| SECRET_KEY | Django SECRET_KEY | "_9*sx..." (local.env)
| DEBUG | Включение debug (локально) | 1
| DB_HOST | Хост БД | postgres
| DB_PORT | Порт БД | 5432
| POSTGRES_USER | Пользователь БД | postgres_user
| POSTGRES_PASSWORD | Пароль БД | posgres_password
| POSTGRES_DB | Название БД | postgres_db
| CELERY_BROKER_URL | Celery broker | redis://redis:6379/0
| CELERY_RESULT_BACKEND | Celery backend | redis://redis:6379/0
| REDIS_HOST | Redis host | redis
| REDIS_PORT | Redis port | 6379
| FLOWER_UNAUTHENTICATED_API | Flower unauthenticated API | true
| FLOWER_BASIC_AUTH | Flower basic auth (user:pass) | admin:admin
| STAGE | Stage label для deploy | "local"

(Файл: local.env в корне репозитория)

8. Тесты

- Запуск внутри контейнера (локально):

  docker exec bh_app_local pytest
  docker exec bh_app_local pytest --cov=app

- Порог покрытия: 70% (см. app/pytest.ini: --cov-fail-under=70)

9. CI/CD (GitHub Actions)

- .github/workflows/pr_tests.yml — тесты на PR (запускает локальный docker stack и pytest; пропускает, если изменились только .md файлы)
- .github/workflows/deploy_dev.yml — автодеплой на DEV (runs-on: self-hosted, backuphub-dev). Шаги: git fetch/checkout/pull, docker compose -f deploy.docker-compose.yml down && up -d --build, docker image prune, ps, curl (файл: .github/workflows/deploy_dev.yml)
- .github/workflows/telegram_notify.yml — уведомления в Telegram о push/PR (использует secrets TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID)

10. Troubleshooting (быстрое решение минимум 5 кейсов)

- PermissionError на vol/static — в локальном старте убрать запуск collectstatic (если есть) или выставить корректные права на vol/static. (Проверить локальные start-скрипты в compose/)
- postgres not ready — entrypoint ждёт БД (compose/entrypoint использует nc -z для ожидания: см. compose/entrypoint)
- celery worker not available — Flower ждёт ping / зависит от celery_worker и celery_beat (см. local.docker-compose.yml: flower depends_on celery_worker, celery_beat)
- Сброс БД (локально):

  docker compose -f local.docker-compose.yml down -v

- Oткрыть shell Django:

  docker exec -it bh_app_local python manage.py shell

Контрольные вопросы (ответы — обязательно изучить код и дать ссылку)

1) Зачем версионирование? Почему у TargetSystem и BackupConfiguration есть отдельные таблицы версий? Что даёт поле is_current?

Ответ: Версионирование выделено в отдельные таблицы (TargetSystemVersion и BackupConfigurationVersion) чтобы хранить историю изменений и мета‑поля (version_number, valid_from, valid_to, owner/administrator, параметры конфигурации). Это видно в моделях: app/systems/models.py и app/configurations/models.py.
Поле is_current отмечает актуальную версию, которую сервис использует при создании новых BackupOperation (см. свойства current_version в моделях: метод current_version возвращает .versions.filter(is_current=True).first()). valid_from/valid_to дают возможность хранить периоды валидности.

2) Почему BackupOperation ссылается на BackupConfigurationVersion, а не на BackupConfiguration? Что это даёт?

Ответ: BackupOperation хранит снимок конкретной версии конфигурации, по которой выполнялся бэкап. Ссылка на BackupConfigurationVersion обеспечивает детерминированность: в Operation фиксируются параметры, использованные в момент выполнения (backup_tool, retention, rpo/rto и т.д.). См. app/operations/models.py (backup_configuration_version FK) и логику создания в BackupOperationCreateSerializer (app/api/v1/backup_operations/serializers.py), где при создании берётся current_version.

3) Как работает аутентификация API? Открой app/api/authentication.py. Объясни, почему authenticate() возвращает (None, system), а не (user, system).

Ответ: ApiKeyAuthentication ищет X-API-Key в request.META и загружает соответствующий TargetSystem (app/api/authentication.py). В DRF результат authenticate() — кортеж (user, auth). Здесь вместо Django User возвращается None, а объект TargetSystem передаётся как request.auth. Так сделано намеренно: нет привязки к пользователю, запросы аутентифицируются системой; permissions и throttling могут читать request.auth (TargetSystem). Файл: app/api/authentication.py (метод authenticate возвращает (None, system)).

4) Как IsOwnerSystem понимает, что операция принадлежит системе-запросчику? Открой app/api/permissions.py. Найди метод _get_target_system и объясни цепочку связей.

Ответ: В методе IsOwnerSystem._get_target_system цепочка связей идёт через объект операции: obj.backup_configuration_version.backup_configuration.target_system_version.target_system. Сравнивается PK request.auth.pk с этим target_system.pk. См. app/api/permissions.py (метод _get_target_system).

5) Почему нельзя изменить завершённую операцию? Найди в BackupOperationUpdateSerializer.validate() проверку и объясни, почему она нужна.

Ответ: В validate() есть проверка: if instance.status in ('success', 'error'): raise ValidationError('Cannot modify a completed operation.'). Это предотвращает изменение уже завершённых записей (чтобы история результатов оставалась неизменной). См. app/api/v1/backup_operations/serializers.py (BackupOperationUpdateSerializer.validate).

6) Что вернётся при PATCH с status=FAILED без error_message? Найди проверку в сериализаторе.

Ответ: Сериализатор вернёт 400 с validation error по полю error_message — в validate() есть проверка, требующая error_message если новый статус == 'FAILED' (строки около 112–117 в serializers.py).

7) Зачем entrypoint ждёт PostgreSQL через nc -z? Что будет, если убрать эту проверку?

Ответ: В compose/entrypoint есть цикл while ! nc -z -w 1 "${DB_HOST}" ${DB_PORT}; do ... done — это гарантирует, что контейнер приложения не запустит миграции и gunicorn до готовности БД. Если убрать — миграции/старты могут упасть с ошибкой подключения к БД и приложение не стартует корректно.

8) Чем local.docker-compose.yml отличается от docker-compose.yml? Найди минимум 3 отличия.

Ответ: В репозитории отсутствует файл docker-compose.yml, поэтому прямого сравнения сделать нельзя. Вместо этого можно сравнить local.docker-compose.yml и deploy.docker-compose.yml (оба в корне):
- env_file: local.docker-compose.yml использует local.env; deploy.docker-compose.yml использует ./.env
- Публикация портов: local.docker-compose.yml мапит порты на хост ("8000:8000", "5555:5555"); в deploy.docker-compose.yml используются expose (внутренние порты) и внешний сетевой бридж
- Dockerfile: local.docker-compose.yml указывает compose/local.Dockerfile; deploy.docker-compose.yml — compose/Dockerfile
- Имена контейнеров: local → bh_app_local; deploy → app_${STAGE}

(Файлы: local.docker-compose.yml и deploy.docker-compose.yml в корне.)

9) Что делает deploy_dev.yml на self-hosted runner? Какие команды он выполняет?

Ответ: Файл .github/workflows/deploy_dev.yml выполняет на self-hosted runner следующие шаги (см. .github/workflows/deploy_dev.yml):
- git fetch origin DEV; git checkout DEV; git pull --ff-only origin DEV
- docker compose -f deploy.docker-compose.yml down --remove-orphans
- docker compose -f deploy.docker-compose.yml up -d --build
- docker image prune -f
- docker compose -f deploy.docker-compose.yml ps
- curl -k -I https://dev.backuphub.spb.ru/ (см. файл workflow)

10) Где генерируется api_key? Найди в модели TargetSystem и объясни, почему editable=False.

Ответ: api_key генерируется автоматически полем UUIDField: default=uuid.uuid4, editable=False, unique=True (app/systems/models.py). editable=False защищает поле от редактирования через Django admin/forms и сигнализирует, что ключ должен быть сгенерирован системой (не вводиться вручную). Это уменьшает риск человеческой ошибки и утечки.

