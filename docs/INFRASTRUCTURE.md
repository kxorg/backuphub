# BackupHub. Infrastructure

Документ описывает серверы, сети, контейнеры, порты и внешние endpoints BackupHub.

Смежные документы:

- [ARCHITECTURE.md](ARCHITECTURE.md) - связи компонентов и архитектурные решения.
- [DEPLOYMENT.md](DEPLOYMENT.md) - CI/CD, deploy и rollback.
- [MONITORING.md](MONITORING.md) - метрики, логи, алерты и dashboards.
- [SECURITY.md](SECURITY.md) - SSH, firewall, секреты, TLS и access control.
- [BACKUPS.md](BACKUPS.md) - backup/restore стратегия.
- [RUNBOOK.md](RUNBOOK.md) - действия при инцидентах.

## 1. Серверы

| Параметр | `dev` | `prod` | `infra` | `secops` |
| :--- | :--- | :--- | :--- | :--- |
| Hostname | `dev.backuphub.spb.ru` | `prod.backuphub.spb.ru` | `infra.backuphub.spb.ru` | `secops.backuphub.spb.ru` |
| IP | `130.49.129.180/24` | `153.80.184.132/24` | `78.17.144.232/24` | `157.22.230.253/24` |
| OS | Ubuntu 22.04.5 LTS | Ubuntu 22.04.2 LTS | Ubuntu 24.04 LTS | Ubuntu 22.04 LTS |
| SSH | `8228` | `8228` | `8228` | `8228` |
| RAM | 1 GB | 1 GB | 2 GB | 1 GB |
| Disk | 15 GB ext4 | 15 GB ext4 | 15 GB ext4 | 15 GB ext4 |
| Назначение | DEV-контур приложения | PROD-контур приложения | Monitoring, logs, alerts, MinIO | CI/CD, registry, DevSecOps |

## 2. Разделение контуров

`dev` принимает актуальную версию из ветки `DEV` и используется для проверки deploy, контейнеров и интеграций.

`prod` обслуживает стабильную версию приложения и production-данные.

`infra` не обслуживает пользовательские запросы BackupHub. Он хранит мониторинг, логи, алерты, Vaultwarden и MinIO.

`secops` добавлен как отдельный контур развития CI/CD. В текущей рабочей схеме build приложения еще выполняется на сервере назначения (`dev`/`prod`). Целевая модель переносит build, registry и security scanning на `secops`.

## 3. Docker layout на DEV/PROD

На `dev` и `prod` сервисы разделены на три compose-контура.

| Директория | Назначение | Жизненный цикл |
| --- | --- | --- |
| `/opt/backuphub/app` | Django, Celery Worker, Celery Beat, Flower | Пересобирается и перезапускается при deploy приложения |
| `/opt/backuphub/database` | PostgreSQL, Redis | Stateful-контур, не пересоздается при deploy приложения |
| `/opt/backuphub/infra` | Nginx, Certbot, Node Exporter, cAdvisor, Grafana Alloy | Инфраструктурный контур, работает постоянно |

Stateful-сервисы вынесены отдельно, чтобы deploy приложения не трогал PostgreSQL и Redis.

## 4. Docker-сеть

Все compose-файлы на сервере подключаются к общей сети:

```yaml
networks:
  backuphub_network:
    external: true
```

Сеть создается один раз:

```bash
docker network create backuphub_network
```

За счет общей сети:

- Nginx из infra-compose проксирует запросы в app-compose;
- Django обращается к PostgreSQL и Redis по service/container name;
- Node Exporter, cAdvisor и Grafana Alloy могут работать независимо от deploy приложения.

## 5. Контейнеры DEV/PROD

| Контейнер | Порт | Назначение |
| --- | --- | --- |
| Nginx | `80`, `443` | Public reverse proxy |
| Django / DRF | `8000` internal | Web UI, REST API, Swagger/ReDoc |
| PostgreSQL 16 | `5432` internal | Основная БД BackupHub |
| Redis | `6379` internal | Celery broker/result backend |
| Celery Worker | internal | Фоновые задачи |
| Celery Beat | internal | Периодические задачи |
| Flower | `5555` internal/admin | UI для Celery |
| Certbot | internal | Let's Encrypt сертификаты |
| Grafana Alloy | `12345` internal | Сбор Docker/Nginx/system logs и отправка в Loki |
| Node Exporter | `9100` protected | Метрики ОС, доступ только Prometheus с `infra` |
| cAdvisor | `8080` protected | Метрики контейнеров, доступ только Prometheus с `infra` |

## 6. Контейнеры INFRA

| Контейнер | Порт | Назначение |
| --- | --- | --- |
| Prometheus | `9090` | Сбор и хранение метрик |
| Grafana | `3000` | Dashboards и Explore |
| Loki | `3100` | Хранилище логов |
| Alertmanager | `9093` | Маршрутизация алертов в Telegram |
| MinIO | `9000`, `9001` | S3-compatible storage для backup PostgreSQL |
| Node Exporter | `9100` | Метрики infra-хоста |
| cAdvisor | `8080` | Метрики infra-контейнеров |
| Grafana Alloy | `12345` | Отправка infra-логов в Loki |
| Nginx | `80`, `443` | HTTPS reverse proxy для UI и Loki ingest |
| Certbot | internal | Let's Encrypt сертификаты |
| Vaultwarden | `80` internal | Хранилище секретов команды |

## 7. SECOPS

`secops` предназначен для build, registry и DevSecOps-практик.

| Контейнер / сервис | Порт | Назначение |
| --- | --- | --- |
| Nginx | `80`, `443` | HTTPS reverse proxy |
| Docker Registry | `5000` internal | Хранилище Docker-образов |
| GitHub Runner | systemd service | Build/deploy/security workflows |
| Grafana Alloy | `12345` internal | Отправка логов `secops` в Loki |
| Node Exporter | `9100` protected | Метрики ОС для Prometheus |
| cAdvisor | `8080` protected | Метрики контейнеров для Prometheus |
| Semgrep / Grype / OWASP ZAP | on demand | Security checks по мере внедрения целевой схемы |

Registry является частью целевой CI/CD-модели. До переключения deploy на registry приложение продолжает собираться на сервере назначения.

## 8. Volumes и постоянные данные

### DEV/PROD

| Volume | Host path | Container path | Назначение |
| --- | --- | --- | --- |
| `postgres_data` | `/opt/backuphub/data/postgres` | `/var/lib/postgresql/data` | Данные PostgreSQL |
| `redis_data` | `/opt/backuphub/data/redis` | `/data` | Данные Redis |

Эти volumes нельзя удалять автоматической очисткой.

### INFRA

| Volume | Назначение |
| --- | --- |
| `prometheus_data` | История метрик |
| `grafana_data` | Dashboards, datasources, users |
| `loki_data` | Логи |
| `alertmanager_data` | Silences и notification log |
| `minio_data` | Backup PostgreSQL |
| `vaultwarden_data` | Данные Vaultwarden |

## 9. Nginx endpoints

### DEV

| Endpoint | Куда проксирует | Доступ |
| --- | --- | --- |
| `https://dev.backuphub.spb.ru` | `app_DEV:8000` | Пользователи/dev-команда |
| `https://node-exporter.dev.backuphub.spb.ru/metrics` | `dev-node-exporter:9100/metrics` | Только Prometheus с `infra` |
| `https://cadvisor.dev.backuphub.spb.ru/metrics` | `dev-cadvisor:8080/metrics` | Только Prometheus с `infra` |

### PROD

| Endpoint | Куда проксирует | Доступ |
| --- | --- | --- |
| `https://prod.backuphub.spb.ru` | `app_PROD:8000` | Пользователи |
| `https://node-exporter.prod.backuphub.spb.ru/metrics` | `prod-node-exporter:9100/metrics` | Только Prometheus с `infra` |
| `https://cadvisor.prod.backuphub.spb.ru/metrics` | `prod-cadvisor:8080/metrics` | Только Prometheus с `infra` |

### INFRA

| Endpoint | Куда проксирует | Защита |
| --- | --- | --- |
| `https://grafana.backuphub.spb.ru` | `grafana:3000` | Nginx Basic Auth + Grafana login |
| `https://prometheus.backuphub.spb.ru` | `prometheus:9090` | Nginx Basic Auth |
| `https://alertmanager.backuphub.spb.ru` | `alertmanager:9093` | Nginx Basic Auth |
| `https://minio.backuphub.spb.ru` | `minio:9001` | Nginx Basic Auth + MinIO login |
| `https://s3.backuphub.spb.ru` | `minio:9000` | Для backup jobs |
| `https://vaultwarden.backuphub.spb.ru` | `vaultwarden:80` | Аутентификация Vaultwarden |
| `https://infra.backuphub.spb.ru/loki/api/v1/push` | `loki:3100/loki/api/v1/push` | IP allowlist для Alloy |

### SECOPS

| Endpoint | Куда проксирует | Доступ |
| --- | --- | --- |
| `https://registry.backuphub.spb.ru` | `registry:5000` | Целевая модель; только CI/CD runners и deploy-серверы |
| `https://node-exporter.secops.backuphub.spb.ru/metrics` | `secops-node-exporter:9100/metrics` | Только Prometheus с `infra` |
| `https://cadvisor.secops.backuphub.spb.ru/metrics` | `secops-cadvisor:8080/metrics` | Только Prometheus с `infra` |

## 10. Порты

### Публичные

| Сервер | Порт | Назначение |
| --- | --- | --- |
| `dev` | `80`, `443` | HTTP/HTTPS приложения и protected metrics endpoints |
| `prod` | `80`, `443` | HTTP/HTTPS приложения и protected metrics endpoints |
| `infra` | `80`, `443` | Monitoring UI, MinIO, Vaultwarden, Loki ingest |
| `secops` | `80`, `443` | Registry и SecOps web endpoints |
| `dev/prod/infra/secops` | `8228` | SSH для администраторов |

### Внутренние и административные

| Порт | Сервис | Доступ |
| --- | --- | --- |
| `8000` | Django | Только Docker Compose / Nginx |
| `5555` | Flower | Только admin-доступ |
| `5432` | PostgreSQL | Только Docker Compose |
| `6379` | Redis | Только Docker Compose |
| `12345` | Grafana Alloy | Local/internal |
| `9100` | Node Exporter | Только Prometheus с `infra` |
| `8080` | cAdvisor | Только Prometheus с `infra` |
| `3100` | Loki | Ingest через infra Nginx |
| `9090` | Prometheus | UI через infra Nginx |
| `9093` | Alertmanager | UI через infra Nginx |
| `3000` | Grafana | UI через infra Nginx |
| `9000` | MinIO API | S3 API через `s3.backuphub.spb.ru` |
| `9001` | MinIO Console | UI через `minio.backuphub.spb.ru` |
| `5000` | Docker Registry | Через `registry.backuphub.spb.ru` |

## 11. Проверочные команды

Проверить контейнеры:

```bash
docker ps
```

Проверить Docker-сети:

```bash
docker network ls
docker network inspect backuphub_network
```

Проверить volumes:

```bash
docker volume ls
docker system df
```

Проверить слушающие порты:

```bash
ss -tulpen
```
