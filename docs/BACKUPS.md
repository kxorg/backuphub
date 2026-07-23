# BackupHub. Backups

Документ описывает, как устроены резервные копии внутренних PostgreSQL-баз BackupHub с помощью WAL-G.

## 1. Что мы бэкапим

BackupHub не выполняет backup внешних систем и не хранит архивы внешних серверов. Его задача - учитывать операции резервного копирования и показывать их статус.

Отдельно от этого у нас есть технические backup собственных PostgreSQL-баз проекта:

| Контур | Что бэкапится | Хранилище |
| --- | --- | --- |
| `dev` | PostgreSQL BackupHub dev | MinIO bucket `backuphub-postgres-dev` |
| `prod` | PostgreSQL BackupHub prod | MinIO bucket `backuphub-postgres-prod` |

## 2. Где хранятся backup

Целевое хранилище - MinIO на `infra.backuphub.spb.ru`.

| Endpoint | Назначение |
| --- | --- |
| `https://minio.backuphub.spb.ru` | Web UI MinIO |
| `https://s3.backuphub.spb.ru` | S3 API для WAL-G и backup jobs |

MinIO S3 API используется как S3-compatible storage. В переменных WAL-G он выглядит как обычный S3 endpoint:

```bash
AWS_ENDPOINT=https://s3.backuphub.spb.ru
AWS_S3_FORCE_PATH_STYLE=true
WALG_S3_PREFIX=s3://backuphub-postgres-prod/walg
```

`AWS_ACCESS_KEY_ID` и `AWS_SECRET_ACCESS_KEY` в этом контексте - это не ключи Amazon AWS, а MinIO access key и secret key. Они должны храниться только на сервере в закрытом env-файле.

## 3. Текущий подход

Для PostgreSQL используется WAL-G.

Сейчас WAL-G установлен на хосте `dev` и `prod`, а PostgreSQL работает в Docker-контейнере. Чтобы WAL-G на хосте видел тот же путь, который PostgreSQL видит внутри контейнера, на хосте создан symlink:

```text
/var/lib/postgresql/data -> /var/lib/docker/volumes/database_postgres_data/_data
```

Внутри контейнера PostgreSQL этот же volume примонтирован как:

```text
/var/lib/docker/volumes/database_postgres_data/_data -> /var/lib/postgresql/data
```

Это важно: WAL-G сравнивает путь, переданный в `backup-push`, с тем, что PostgreSQL возвращает через `show data_directory`. Поэтому на хосте используется путь `/var/lib/postgresql/data`, а не прямой путь `/var/lib/docker/volumes/.../_data`.

## 4. Что делает WAL-G

WAL-G делает физический backup PostgreSQL data directory и отправляет результат в MinIO.

Поток выглядит так:

```text
cron
  -> /usr/local/sbin/backuphub-postgres-walg-backup.sh
  -> POST /api/v1/backup-operations/ в BackupHub
  -> wal-g backup-push /var/lib/postgresql/data
  -> MinIO S3 API https://s3.backuphub.spb.ru
  -> PATCH /api/v1/backup-operations/{id}/ в BackupHub
```

Backup состоит из объектов WAL-G в bucket. Имена вида:

```text
base_000000010000000000000009
base_000000010000000000000009_backup_stop_sentinel.json
```

Это нормальные технические имена WAL-G. Они строятся вокруг timeline/LSN PostgreSQL. Человекочитаемое имя отдельно не добавляем: смотреть удобнее через BackupHub, где в metadata записывается `backup_name`, размер, статус и S3 path.

## 5. Что сейчас не настроено

Point-in-time recovery сейчас не является целевой схемой.

На `dev` и `prod` `archive_mode` сейчас выключен:

```sql
show archive_mode;
-- off
```

Это означает:

- restore возможен на границу последнего успешного base backup;
- восстановление на произвольную минуту между backup не поддерживается;
- WAL-G может выводить warning про `archive_mode is not enabled`.

Если появится требование PITR, нужно будет включить WAL archiving в PostgreSQL:

```conf
archive_mode = on
archive_command = 'wal-g wal-push %p'
```

При текущем требовании "допустима потеря данных до периода между backup" достаточно регулярных физических backup, но restore test все равно обязателен.

## 6. Где лежат файлы на серверах

На `dev` и `prod` используется одинаковая структура.

| Путь | Назначение |
| --- | --- |
| `/usr/local/bin/wal-g` | бинарник WAL-G |
| `/usr/local/sbin/backuphub-postgres-walg-backup.sh` | wrapper-скрипт backup |
| `/etc/wal-g/dev.env` | настройки WAL-G для dev |
| `/etc/wal-g/prod.env` | настройки WAL-G для prod |
| `/etc/backuphub/dev.env` | настройки отправки результата dev backup в BackupHub API |
| `/etc/backuphub/prod.env` | настройки отправки результата prod backup в BackupHub API |
| `/etc/cron.d/backuphub-postgres-walg` | cron-задание регулярного backup, создается при включении расписания |
| `/var/log/backuphub-postgres-walg-backup.log` | лог запуска backup, появляется после ручного или cron-запуска |
| `/var/lib/postgresql/data` | symlink на Docker volume PostgreSQL |

## 7. WAL-G env

Пример `/etc/wal-g/prod.env`:

```bash
AWS_ACCESS_KEY_ID=CHANGE_ME
AWS_SECRET_ACCESS_KEY=CHANGE_ME
AWS_ENDPOINT=https://s3.backuphub.spb.ru
AWS_REGION=us-east-1
AWS_S3_FORCE_PATH_STYLE=true

WALG_S3_PREFIX=s3://backuphub-postgres-prod/walg
WALG_COMPRESSION_METHOD=zstd
WALG_UPLOAD_CONCURRENCY=4
WALG_DOWNLOAD_CONCURRENCY=4

PGHOST=127.0.0.1
PGPORT=5432
PGUSER=backuphub_app
PGPASSWORD=CHANGE_ME
PGDATABASE=backuphub_prod
PGDATA=/var/lib/postgresql/data
```

Для `dev` меняются bucket и параметры подключения к dev PostgreSQL:

```bash
WALG_S3_PREFIX=s3://backuphub-postgres-dev/walg
PGUSER=postgres_user
PGDATABASE=postgres_db
PGDATA=/var/lib/postgresql/data
```

Так как WAL-G запускается на хосте, PostgreSQL должен быть доступен с хоста. В database compose порт PostgreSQL публикуется только на localhost:

```yaml
ports:
  - "127.0.0.1:5432:5432"
```

Так порт не торчит наружу, но backup job на хосте может подключиться к базе через `127.0.0.1:5432`.

## 8. BackupHub env

Пример `/etc/backuphub/prod.env`:

```bash
BACKUPHUB_API_URL=https://prod.backuphub.spb.ru
BACKUPHUB_API_KEY=CHANGE_ME
BACKUPHUB_BACKUP_CONFIGURATION_ID=1

BACKUPHUB_HOSTNAME=prod.backuphub.spb.ru
BACKUPHUB_IP_ADDRESS=153.80.184.132
BACKUPHUB_STORAGE_TYPE=s3
```

Пример `/etc/backuphub/dev.env`:

```bash
BACKUPHUB_API_URL=https://prod.backuphub.spb.ru
BACKUPHUB_API_KEY=CHANGE_ME
BACKUPHUB_BACKUP_CONFIGURATION_ID=2

BACKUPHUB_HOSTNAME=dev.backuphub.spb.ru
BACKUPHUB_IP_ADDRESS=130.49.129.180
BACKUPHUB_STORAGE_TYPE=s3
```

Смысл этих переменных:

| Переменная | Назначение |
| --- | --- |
| `BACKUPHUB_API_URL` | куда отправлять информацию о backup operation |
| `BACKUPHUB_API_KEY` | API key системы/конфигурации BackupHub |
| `BACKUPHUB_BACKUP_CONFIGURATION_ID` | ID backup configuration в BackupHub |
| `BACKUPHUB_HOSTNAME` | hostname сервера, который делает backup |
| `BACKUPHUB_IP_ADDRESS` | IP сервера |
| `BACKUPHUB_STORAGE_TYPE` | тип хранилища, сейчас `s3` |

## 9. Как работает wrapper-скрипт

Скрипт `/usr/local/sbin/backuphub-postgres-walg-backup.sh` делает не просто `wal-g backup-push`, а полный цикл учета backup в BackupHub.

Шаги:

1. Загружает `/etc/wal-g/<stage>.env`.
2. Загружает `/etc/backuphub/<stage>.env`.
3. Проверяет обязательные переменные и наличие `wal-g`, `curl`, `python3`.
4. Создает backup operation в BackupHub:

```http
POST /api/v1/backup-operations/
```

5. Запускает:

```bash
wal-g backup-push "$PGDATA"
```

6. Если backup упал, отправляет в BackupHub:

```json
{
  "status": "failed",
  "error_message": "tail of backup log"
}
```

7. Если backup успешен, получает список backup:

```bash
wal-g backup-list --json --detail
```

8. Отправляет в BackupHub:

```json
{
  "status": "success",
  "size_bytes": 2127058,
  "storage_type": "s3",
  "storage_path": "s3://backuphub-postgres-prod/walg/basebackups_005/base_...",
  "metadata": {
    "tool": "wal-g",
    "backup_name": "base_..."
  }
}
```

## 10. Как запустить backup вручную

На `prod`:

```bash
sudo WALG_ENV_FILE=/etc/wal-g/prod.env \
     BACKUPHUB_ENV_FILE=/etc/backuphub/prod.env \
     /usr/local/sbin/backuphub-postgres-walg-backup.sh
```

На `dev`:

```bash
sudo WALG_ENV_FILE=/etc/wal-g/dev.env \
     BACKUPHUB_ENV_FILE=/etc/backuphub/dev.env \
     /usr/local/sbin/backuphub-postgres-walg-backup.sh
```

Посмотреть список backup в MinIO через WAL-G:

```bash
sudo bash -lc 'set -a; . /etc/wal-g/prod.env; set +a; wal-g backup-list --detail'
```

Для `dev` заменить файл на `/etc/wal-g/dev.env`.

## 11. Cron

Пример cron-задания:

```cron
15 3 * * * root WALG_ENV_FILE=/etc/wal-g/prod.env BACKUPHUB_ENV_FILE=/etc/backuphub/prod.env /usr/local/sbin/backuphub-postgres-walg-backup.sh >> /var/log/backuphub-postgres-walg-backup.log 2>&1
```

Для `dev`:

```cron
30 3 * * * root WALG_ENV_FILE=/etc/wal-g/dev.env BACKUPHUB_ENV_FILE=/etc/backuphub/dev.env /usr/local/sbin/backuphub-postgres-walg-backup.sh >> /var/log/backuphub-postgres-walg-backup.log 2>&1
```

Проверка cron:

```bash
sudo cat /etc/cron.d/backuphub-postgres-walg
sudo tail -f /var/log/backuphub-postgres-walg-backup.log
```

