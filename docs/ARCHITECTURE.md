# BackupHub. Architecture

Документ объясняет, как связаны компоненты BackupHub и почему система устроена именно так.

## 1. Границы ответственности BackupHub

BackupHub - централизованная система мониторинга и учета резервного копирования.

BackupHub делает:

- принимает статусы backup-операций через REST API;
- хранит историю операций;
- хранит сведения о системах, серверах, backup tools и окружениях;
- показывает web-интерфейс, журнал операций и статистику;
- предоставляет Swagger/ReDoc для API;
- помогает централизованно контролировать процессы резервного копирования.

BackupHub не делает:

- не выполняет backup внешних систем;
- не хранит архивы внешних систем;
- не заменяет backup-agent или backup-систему;
- не является единственным источником restore-процедур для внешних систем.

Отдельно: MinIO в инфраструктуре BackupHub используется для технических backup наших внутренних PostgreSQL-баз, а не для хранения архивов внешних систем.

## 2. Диаграммы

Редактируемая схема:

- [main.drawio](main.drawio)

PNG для быстрого просмотра:

![BackupHub infrastructure](infrastructure-overview.png)

Текущая CI/CD-схема:

![CI/CD before SecOps](ci-cd-before-secops.png)

Целевая CI/CD-схема после внедрения `secops`:

![CI/CD after SecOps](ci-cd-after-secops.png)

GitHub runners:

![GitHub runners](github-runners.png)

## 3. Верхнеуровневая топология

Инфраструктура состоит из четырех серверов:

- `dev.backuphub.spb.ru` - тестовый контур приложения.
- `prod.backuphub.spb.ru` - production-контур приложения.
- `infra.backuphub.spb.ru` - мониторинг, логи, алерты, MinIO, Vaultwarden.
- `secops.backuphub.spb.ru` - целевой контур для CI/CD, registry и DevSecOps.

Логическая схема:

```text
Users / external backup tools
  -> Nginx on dev/prod
  -> Django / DRF
  -> PostgreSQL
  -> Redis / Celery

dev/prod/secops agents
  -> Prometheus on infra
  -> Loki on infra
  -> Grafana on infra

PostgreSQL backups
  -> MinIO on infra
```

## 4. Основные компоненты

| Компонент | Назначение |
| --- | --- |
| Django / DRF | Web UI и REST API |
| PostgreSQL | Основное хранилище бизнес-данных BackupHub |
| Redis | Celery broker и result backend |
| Celery Worker | Фоновые задачи |
| Celery Beat | Периодические задачи |
| Flower | Административный UI Celery |
| Nginx | Единственная публичная HTTP/HTTPS-точка входа |
| Prometheus | Сбор метрик |
| Grafana | Dashboards и Explore |
| Loki | Централизованное хранение логов |
| Grafana Alloy | Доставка логов в Loki |
| Alertmanager | Маршрутизация алертов в Telegram |
| MinIO | S3-compatible storage для backup PostgreSQL |
| Vaultwarden | Внутреннее хранилище секретов команды |

## 5. Сетевые потоки

### Web/API

```text
Internet
  -> dev/prod Nginx :443
  -> app_DEV/app_PROD :8000
  -> PostgreSQL :5432
```

Nginx завершает TLS, выполняет HTTP -> HTTPS redirect и проксирует запросы в Django. Django не должен быть доступен напрямую извне.

### Celery

```text
Django / Celery Beat
  -> Redis :6379
  -> Celery Worker
  -> PostgreSQL :5432
```

Redis используется как очередь и backend результатов. Worker выполняет фоновые задачи и пишет результат в PostgreSQL при необходимости.

### Logs

```text
Grafana Alloy on dev/prod/infra/secops
  -> https://infra.backuphub.spb.ru/loki/api/v1/push
  -> infra Nginx :443
  -> Loki :3100
```

Endpoint `/loki/api/v1/push` предназначен только для приема логов от Alloy и должен быть ограничен allowlist по IP.

### Metrics

```text
Prometheus on infra
  -> protected node-exporter/cadvisor endpoints on dev
  -> protected node-exporter/cadvisor endpoints on prod
  -> protected node-exporter/cadvisor endpoints on secops
  -> local node-exporter/cadvisor on infra
```

Prometheus работает по pull-модели: он сам забирает метрики с серверов.

### Backups

```text
PostgreSQL dev/prod/DefectDojo
  -> backup job
  -> MinIO S3 API
  -> backup bucket
```

MinIO используется как централизованное S3-compatible хранилище для backup внутренних PostgreSQL-баз.

## 6. Архитектурные решения

### Разделение на dev/prod/infra/secops

Решение: разделить приложение, мониторинг и CI/CD по разным серверам.

Причина: маленькие ресурсы серверов и разные жизненные циклы. Приложение обновляется часто, мониторинг должен жить независимо, build/security tasks лучше вынести отдельно.

Следствие: отказ или перегрузка deploy-сервера не должна ломать мониторинг.

### Stateful-сервисы вынесены из app-compose

Решение: PostgreSQL и Redis запускаются отдельным compose-контуром.

Причина: deploy приложения не должен пересоздавать БД и Redis.

Следствие: app-compose можно пересобирать и перезапускать чаще, не трогая данные.

### Nginx как единая публичная точка входа

Решение: все web-интерфейсы и технические endpoints публикуются через Nginx.

Причина: TLS, Basic Auth, allowlist, redirect и proxy headers должны управляться централизованно.

Следствие: внутренние порты контейнеров не должны быть публичной поверхностью атаки.

### Метрики через protected endpoints

Решение: Node Exporter и cAdvisor доступны только Prometheus с `infra`.

Причина: endpoints метрик раскрывают чувствительную техническую информацию о хосте и контейнерах.

Следствие: доступ ограничивается Nginx allowlist и firewall/iptables.

### MinIO только для внутренних backup

Решение: MinIO хранит backup PostgreSQL с `dev`, `prod` и PostgreSQL DefectDojo.

Причина: BackupHub не является хранилищем архивов внешних систем, но собственные базы должны быть восстановимы.

Следствие: MinIO credentials не хранятся в git, restore должен периодически проверяться.

### Текущий build на сервере назначения, целевой build на secops

Решение сейчас: образ собирается на `dev`/`prod`, где потом запускается контейнер.

Целевая модель: build, SAST/SCA checks и push образа выполняются на `secops`, deploy-серверы только скачивают готовый image из registry.

Причина: build cache и runner могут забивать диск на app-серверах; security gates удобнее держать в отдельном контуре.

## 7. Правило актуальности

Любой PR, меняющий инфраструктуру, deployment, monitoring, security или backup-логику, должен обновлять соответствующий документ:

- архитектурные связи - `ARCHITECTURE.md`;
- серверы, сети, endpoints, ports - `INFRASTRUCTURE.md`;
- workflows и deploy - `DEPLOYMENT.md`;
- алерты, dashboards, логи - `MONITORING.md`;
- SSH/firewall/secrets/TLS - `SECURITY.md`;
- backup/restore - `BACKUPS.md`;
- аварийные инструкции - `RUNBOOK.md`.
