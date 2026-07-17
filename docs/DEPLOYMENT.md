# BackupHub. Deployment

Документ описывает, как код попадает из GitHub на `dev` и `prod`, какие workflows используются и что делать при падении deploy.

## 1. GitHub Actions workflows

| Workflow | Файл | Назначение |
| --- | --- | --- |
| PR checks | [../.github/workflows/pr_tests.yml](../.github/workflows/pr_tests.yml) | Проверка pull request перед merge |
| Deploy DEV | [../.github/workflows/deploy_dev.yml](../.github/workflows/deploy_dev.yml) | Deploy актуальной ветки `DEV` на `dev` |
| Telegram notify | [../.github/workflows/telegram_notify.yml](../.github/workflows/telegram_notify.yml) | Уведомления о PR/push событиях |

Compose-файлы:

| Файл | Назначение |
| --- | --- |
| [../test.docker-compose.yml](../test.docker-compose.yml) | Минимальный контур для CI-тестов |
| [../local.docker-compose.yml](../local.docker-compose.yml) | Локальная разработка |
| [../deploy.docker-compose.yml](../deploy.docker-compose.yml) | Deploy на серверы |

## 2. Pull Request checks

PR в `DEV` проверяется на GitHub-hosted runner.

```text
Pull Request to DEV
  -> actions/checkout
  -> docker compose -f test.docker-compose.yml up -d --wait
  -> ruff check
  -> pytest
  -> docker compose -f test.docker-compose.yml down -v
```

Тестовый compose должен поднимать только то, что нужно для проверки: `app`, `postgres`, `redis`.

Тесты запускаются внутри app-контейнера:

```bash
docker compose -f test.docker-compose.yml exec -T app pytest --cov=app --cov-report=term-missing
```

`-T` отключает pseudo-TTY. Это нужно для стабильной работы команды внутри GitHub Actions.

Если обязательная проверка не проходит, merge в защищенную ветку должен быть заблокирован branch protection rule.

Для документационных изменений workflow может пропускаться через `paths-ignore` или отдельную job, которая завершает required check успешно без запуска контейнеров.

## 3. Текущий DEV deploy

Сейчас образ собирается прямо на `dev`.

```text
merge / push to DEV
  -> GitHub Actions
  -> self-hosted runner on dev
  -> update code
  -> docker compose build
  -> docker compose up -d --build
  -> prune old images/cache
```

Runner работает как systemd service и управляет локальным Docker Engine.

Базовая логика deploy:

```bash
cd /opt/backuphub/app
git fetch origin DEV
git checkout DEV
git pull --ff-only origin DEV
docker compose -f deploy.docker-compose.yml down --remove-orphans
docker compose -f deploy.docker-compose.yml up -d --build
docker image prune -f
```

Если workflow запускается из working directory `/opt/backuphub/app`, `cd` не нужен.

## 4. Текущий PROD deploy

Production deploy должен идти только после проверки на `dev`.

Рекомендуемый порядок:

```text
release / PROD ref
  -> protected GitHub environment
  -> manual approval
  -> backup PostgreSQL в MinIO
  -> deploy на prod runner
  -> migrations
  -> docker compose up -d
  -> smoke check
  -> cleanup old images/cache
```

Перед production-миграциями нужен свежий backup PostgreSQL. См. [BACKUPS.md](BACKUPS.md).

## 5. Целевая схема с SECOPS

После внедрения `secops` build переносится с `dev/prod` на отдельную машину.

```text
merge / push to DEV
  -> secops runner
  -> build immutable image
  -> SAST / SCA checks
  -> push registry.backuphub.spb.ru/backuphub/app:<commit_sha>
  -> push registry.backuphub.spb.ru/backuphub/app:dev-latest
  -> dev runner
  -> docker pull registry.backuphub.spb.ru/backuphub/app:<commit_sha>
  -> docker compose up -d
  -> health check
```

Теги:

| Tag | Назначение |
| --- | --- |
| `<commit_sha>` | Точная версия кода, удобна для deploy и rollback |
| `dev-latest` | Последняя успешная сборка DEV |
| `prod-latest` | Последняя production-сборка после approval |

Deploy должен предпочитать `<commit_sha>`, а не `latest`, чтобы было понятно, какая версия реально запущена.

## 6. Smoke check

После deploy нужно проверить:

```bash
curl -fsS https://dev.backuphub.spb.ru/ >/dev/null
```

Для production:

```bash
curl -fsS https://prod.backuphub.spb.ru/ >/dev/null
```

Проверить контейнеры:

```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

Проверить логи приложения:

```bash
docker logs --tail=200 app_DEV
```

Имя контейнера зависит от значения `STAGE`.

## 7. Очистка образов

Минимальная очистка после deploy:

```bash
docker image prune -f
```

Если диск забит build cache:

```bash
docker builder prune -af
```

`docker image prune -af` удаляет все неиспользуемые образы, включая образы без dangling-статуса. Команду нельзя запускать вслепую на сервере, где могут быть нужны старые локальные образы для rollback.

## 8. Rollback

### Текущая схема без registry

Rollback выполняется через возврат к предыдущему commit и пересборку:

```bash
cd /opt/backuphub/app
git log --oneline -n 10
git checkout <previous_commit_sha>
docker compose -f deploy.docker-compose.yml up -d --build
```

После стабилизации нужно зафиксировать, какой commit откатили и почему.

### Целевая схема с registry

Rollback выполняется запуском предыдущего image tag:

```bash
export IMAGE_TAG=<previous_commit_sha>
docker compose -f deploy.docker-compose.yml up -d
```

Для этого `deploy.docker-compose.yml` должен использовать image с tag:

```yaml
image: registry.backuphub.spb.ru/backuphub/app:${IMAGE_TAG}
```

## 9. Если deploy упал

1. Открыть failed job в GitHub Actions.
2. Проверить, picked up ли job нужный runner.
3. На сервере проверить runner service:

```bash
systemctl list-units "*runner*"
systemctl status "<runner-service-name>"
```

4. Проверить свободное место:

```bash
df -h
docker system df
```

5. Проверить docker compose:

```bash
cd /opt/backuphub/app
docker compose -f deploy.docker-compose.yml ps
docker compose -f deploy.docker-compose.yml logs --tail=200
```

6. Если проблема в YAML:

```bash
docker compose -f deploy.docker-compose.yml config
```

7. Если проблема в приложении, смотреть [RUNBOOK.md](RUNBOOK.md).

## 10. Правило обновления документации

PR, меняющий workflow, compose deploy, runner labels, ветки deploy или registry flow, должен обновлять этот документ.
