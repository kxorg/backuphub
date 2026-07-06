# GitHub Runner

Документ описывает self-hosted GitHub Actions runners, которые установлены на серверах `dev` и `prod` проекта BackupHub.

В проекте не используется отдельное Docker Registry. Поэтому Docker-образы собираются локально на том сервере, где затем запускаются контейнеры:

```text
GitHub Actions -> GitHub Runner -> docker compose build/up
```

## Оглавление

- [1. Назначение](#1-назначение)
- [2. Где установлены runner-ы](#2-где-установлены-runner-ы)
  - [2.1 DEV](#21-dev)
  - [2.2 PROD](#22-prod)
- [3. Пользователь](#3-пользователь)
- [4. Рабочие директории](#4-рабочие-директории)
- [5. Systemd service](#5-systemd-service)
- [6. Как посмотреть статус runner-а](#6-как-посмотреть-статус-runner-а)
  - [6.1 Через systemd](#61-через-systemd)
  - [6.2 Через скрипт runner-а](#62-через-скрипт-runner-а)
- [7. Как запустить, остановить и перезапустить runner](#7-как-запустить-остановить-и-перезапустить-runner)
- [8. Как посмотреть логи runner-а](#8-как-посмотреть-логи-runner-а)
  - [8.1 Логи systemd](#81-логи-systemd)
  - [8.2 Диагностические логи runner-а](#82-диагностические-логи-runner-а)
- [9. Labels runner-ов](#9-labels-runner-ов)

## 1. Назначение

На серверах `dev` и `prod` установлены self-hosted GitHub Actions runners. Они выполняют workflow прямо на целевых машинах проекта BackupHub.

Основная логика:

```text
GitHub repository
  -> GitHub Actions workflow
  -> self-hosted runner на dev/prod
  -> docker compose build
  -> tests / migrations
  -> docker compose up -d
```

Так как registry нет, после успешного pipeline нужный Docker-образ остается на той же машине. Поэтому на серверах нужна регулярная очистка старых images и build cache, но без удаления volumes.

## 2. Где установлены runner-ы

### 2.1 DEV

| Параметр | Значение |
| --- | --- |
| Сервер | `dev.backuphub.spb.ru` |
| Директория | `/opt/github-runner` |
| Имя runner-а | `backuphub-dev-runner` |
| Label | `backuphub-dev` |
| Назначение | PR checks и deploy в `DEV` |

`dev` runner используется для проверки изменений и развертывания тестового контура. Код из pull request может проверяться здесь, но секреты и production-доступы в таких job использовать нельзя.

### 2.2 PROD

| Параметр | Значение |
| --- | --- |
| Сервер | `prod.backuphub.spb.ru` |
| Директория | `/opt/github-runner` |
| Имя runner-а | `backuphub-prod-runner` |
| Label | `backuphub-prod` |
| Назначение | Deploy в `PROD` после approval |

Код из Pull Request не должен выполняться на `prod` runner-е. Production runner используется только для защищенного deploy после проверки на `dev`.

## 3. Пользователь

Runner запускается от отдельного системного пользователя:

```text
github-runner
```

Пользователь `github-runner` является служебным пользователем и не предназначен для обычного SSH-доступа.

Если runner выполняет Docker-команды, пользователь должен быть добавлен в группу `docker`:

```bash
sudo usermod -aG docker github-runner
```

## 4. Рабочие директории

| Назначение | Путь |
| --- | --- |
| Основная директория runner-а | `/opt/github-runner` |
| Рабочая директория GitHub Actions | `/opt/github-runner/_work` |
| Диагностические логи runner-а | `/opt/github-runner/_diag` |

Обычно руками правят только конфигурацию сервиса или смотрят логи. Содержимое `_work` создается GitHub Actions автоматически.

## 5. Systemd service

Runner установлен как `systemd` service.

| Сервер | Service |
| --- | --- |
| `dev` | `actions.runner.kxorg-backuphub.backuphub-dev-runner.service` |
| `prod` | `actions.runner.kxorg-backuphub.backuphub-prod-runner.service` |


## 6. Как посмотреть статус runner-а

### 6.1 Через systemd

Посмотреть все runner-ы на текущем сервере:

```bash
systemctl status actions.runner*
```

Посмотреть runner на `dev`:

```bash
systemctl status actions.runner.kxorg-backuphub.backuphub-dev-runner.service
```

Посмотреть runner на `prod`:

```bash
systemctl status actions.runner.kxorg-backuphub.backuphub-prod-runner.service
```

### 6.2 Через скрипт runner-а

Перейти в директорию runner-а:

```bash
cd /opt/github-runner
```

Проверить статус:

```bash
sudo ./svc.sh status
```

## 7. Как запустить, остановить и перезапустить runner

Через runner script:

```bash
cd /opt/github-runner
sudo ./svc.sh start
sudo ./svc.sh stop
sudo ./svc.sh status
```

Через `systemd` на `dev`:

```bash
sudo systemctl restart actions.runner.kxorg-backuphub.backuphub-dev-runner.service
systemctl status actions.runner.kxorg-backuphub.backuphub-dev-runner.service
```

Через `systemd` на `prod`:

```bash
sudo systemctl restart actions.runner.kxorg-backuphub.backuphub-prod-runner.service
systemctl status actions.runner.kxorg-backuphub.backuphub-prod-runner.service
```

## 8. Как посмотреть логи runner-а

### 8.1 Логи systemd

Посмотреть логи всех runner-ов в реальном времени:

```bash
journalctl -u actions.runner* -f
```

Посмотреть последние логи:

```bash
journalctl -u actions.runner* -n 100
```

Логи конкретного runner-а на `dev`:

```bash
journalctl -u actions.runner.kxorg-backuphub.backuphub-dev-runner.service -f
```

Логи конкретного runner-а на `prod`:

```bash
journalctl -u actions.runner.kxorg-backuphub.backuphub-prod-runner.service -f
```

### 8.2 Диагностические логи runner-а

Список диагностических логов:

```bash
ls -lah /opt/github-runner/_diag
```

Посмотреть последние строки логов:

```bash
tail -n 100 /opt/github-runner/_diag/*.log
```

Следить за логами в реальном времени:

```bash
tail -f /opt/github-runner/_diag/*.log
```

## 9. Labels runner-ов

Labels используются в GitHub Actions workflow, чтобы job запускалась на нужной машине.

Для `dev` runner:

```text
backuphub-dev
```

Для `prod` runner:

```text
backuphub-prod
```

Рекомендуется всегда указывать и `self-hosted`, и проектный label:

```yaml
runs-on: [self-hosted, backuphub-dev]
```

```yaml
runs-on: [self-hosted, backuphub-prod]
```
