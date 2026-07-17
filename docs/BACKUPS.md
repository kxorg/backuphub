# BackupHub. Backups

Документ описывает backup/restore стратегию внутренних данных BackupHub.

Аудитория: DevOps, лид, ответственные за эксплуатацию.

## 1. Что такое MinIO

MinIO - S3-compatible object storage. Для BackupHub это внутреннее объектное хранилище файловых backup.

BackupHub не хранит архивы внешних систем. MinIO используется для технических backup наших внутренних PostgreSQL-баз.

В MinIO должны попадать:

- backup PostgreSQL с `dev`;
- backup PostgreSQL с `prod`;
- backup PostgreSQL от DefectDojo в `secops`-контуре.

## 2. Что бэкапится

Обязательно:

| Объект | Причина |
| --- | --- |
| PostgreSQL `dev` | Проверка restore и сохранение тестовых данных |
| PostgreSQL `prod` | Основные production-данные BackupHub |
| PostgreSQL DefectDojo | Security findings и history сканирований |
| Nginx configs | Быстрое восстановление reverse proxy |
| Prometheus/Grafana/Loki configs | Восстановление observability |
| GitHub Actions workflows | История хранится в git, но изменения должны проходить review |

Опционально:

| Объект | Комментарий |
| --- | --- |
| Redis | Не является основным бизнес-хранилищем, но может ускорить восстановление фоновых очередей |
| Grafana dashboards | Если dashboards не provisioned из git, нужен backup `grafana_data` |
| Vaultwarden data | Критично для секретов команды, backup должен быть шифрован |

## 3. Инструмент backup

Стартовый инструмент: `pg_dump` в custom format.

Обоснование:

- базы небольшие;
- проще эксплуатация и restore;
- backup легко проверить локально;
- не требуется сложная WAL-инфраструктура на первом этапе.

Формат:

```bash
pg_dump -Fc -h postgres -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f backup.dump
```

Если появится требование point-in-time recovery, стратегия должна быть пересмотрена в сторону WAL-G/WAL archiving.

## 4. Целевое хранилище

Backup складываются в MinIO через S3 API:

```text
backup job
  -> pg_dump
  -> compressed dump
  -> MinIO S3 API
  -> bucket
```

Рекомендуемые buckets:

```text
backuphub-postgres-dev
backuphub-postgres-prod
defectdojo-postgres
```

Credentials для backup job:

- отдельный MinIO access key;
- минимальные права только на нужный bucket;
- секреты не хранятся в git;
- ключи ротируются при смене ответственных или подозрении на компрометацию.

## 5. Расписание

Минимальная политика:

| Контур | Расписание |
| --- | --- |
| `dev` PostgreSQL | 1 раз в сутки |
| `prod` PostgreSQL | 1 раз в сутки + перед миграциями |
| DefectDojo PostgreSQL | 1 раз в сутки |
| configs | при изменении через git/repo infrastructure |

Перед production deploy с миграциями backup PostgreSQL обязателен.

## 6. Retention

Рекомендуемая политика:

| Backup | Retention |
| --- | --- |
| Daily | 14 дней |
| Weekly | 8 недель |
| Before migration | 30 дней |

Retention должен учитывать размер MinIO volume и свободное место на `infra`.

## 7. Именование backup

Формат имени:

```text
<system>/<environment>/<database>/<yyyy-mm-dd>/<timestamp>_<commit_sha>.dump
```

Пример:

```text
backuphub/prod/postgres/2026-07-16/20260716_030000_9cda7b5.dump
```

Для backup вне deploy можно использовать `manual` вместо commit sha.

## 8. Restore test

Backup без проверки restore нельзя считать рабочим.

Минимальная проверка:

```bash
createdb restore_check
pg_restore -d restore_check backup.dump
psql -d restore_check -c "select count(*) from django_migrations;"
dropdb restore_check
```

Частота проверки:

- `dev` - еженедельно;
- `prod` - после настройки регулярных backup, затем не реже 1 раза в месяц;
- DefectDojo - не реже 1 раза в месяц.

## 9. Процедура восстановления PostgreSQL

1. Остановить приложение, которое пишет в БД:

```bash
cd /opt/backuphub/app
docker compose -f deploy.docker-compose.yml down
```

2. Скачать нужный dump из MinIO.

3. Создать пустую базу или очистить целевую БД по согласованию с ответственным.

4. Восстановить:

```bash
pg_restore -h postgres -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists backup.dump
```

5. Запустить приложение:

```bash
docker compose -f deploy.docker-compose.yml up -d
```

6. Проверить:

```bash
curl -fsS https://dev.backuphub.spb.ru/ >/dev/null
docker logs --tail=200 app_DEV
```

Для `prod` вместо `dev.backuphub.spb.ru` использовать production endpoint.

## 10. Restore DefectDojo

Порядок аналогичный PostgreSQL BackupHub:

```text
stop DefectDojo app
restore PostgreSQL dump
start DefectDojo app
check UI and reports
```

Перед восстановлением DefectDojo нужно сохранить текущую БД в отдельный emergency backup.

## 11. Ответственность

Порядок эскалации:

1. Ответственный за инфраструктуру.
2. Backend/DevOps lead.
3. Руководитель проекта.

Актуальные контакты должны быть в закрепленном сообщении командного Telegram-чата.

## 12. Правило обновления

PR, меняющий backup job, MinIO buckets, retention, restore procedure или структуру PostgreSQL deploy, должен обновлять этот документ.
