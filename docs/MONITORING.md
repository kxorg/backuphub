# BackupHub. Monitoring

Документ описывает мониторинг, логи, алерты и dashboards.

Аудитория: DevOps, разработчики при инцидентах, техлиды.

## 1. Компоненты мониторинга

| Компонент | Где работает | Назначение |
| --- | --- | --- |
| Prometheus | `infra` | Сбор и хранение метрик |
| Grafana | `infra` | Dashboards, Explore, datasource UI |
| Loki | `infra` | Хранение логов |
| Grafana Alloy | `dev/prod/infra/secops` | Сбор и отправка логов в Loki |
| Alertmanager | `infra` | Группировка и отправка алертов |
| Node Exporter | все серверы | Метрики ОС |
| cAdvisor | все серверы | Метрики Docker-контейнеров |

## 2. Метрики

Минимальный набор мониторинга:

- доступность серверов;
- CPU;
- RAM;
- disk usage;
- состояние Docker containers;
- доступность PostgreSQL;
- доступность Redis;
- Nginx 5xx;
- срок действия TLS-сертификатов;
- наличие свежего backup PostgreSQL;
- ошибки Grafana Alloy / Loki;
- заполнение диска на `infra`;
- состояние GitHub Runner на self-hosted серверах.

Prometheus работает по pull-модели:

```text
Prometheus on infra
  -> node-exporter / cadvisor on dev
  -> node-exporter / cadvisor on prod
  -> node-exporter / cadvisor on secops
  -> local node-exporter / cadvisor on infra
```

На `dev`, `prod` и `secops` metrics endpoints доступны только Prometheus с IP `infra`.

## 3. Labels для dashboards

cAdvisor должен отдавать нормальные Docker labels:

```text
node=dev|prod|infra|secops
server=dev|prod|infra|secops
container=<docker container name>
service=<docker compose service>
compose_project=<docker compose project>
```

В Grafana dashboard основные фильтры:

- `node`;
- `job`;
- `service`;
- `container`.

Если в фильтрах не виден контейнер, сначала проверить выбранный time range: Grafana/Loki могут показывать только те series/labels, по которым были данные в выбранном диапазоне.

## 4. Логи

Поток логов:

```text
Grafana Alloy on dev/prod/infra/secops
  -> https://infra.backuphub.spb.ru/loki/api/v1/push
  -> Nginx on infra
  -> Loki :3100
```

Alloy читает:

- Docker logs;
- Nginx logs;
- system logs.

Loki ingest endpoint:

```text
https://infra.backuphub.spb.ru/loki/api/v1/push
```

Этот endpoint не является UI. Доступ к нему должен быть ограничен allowlist по IP серверов, где работает Alloy.

## 5. Docker log rotation

Для контейнеров используется стандартный Docker logging driver `json-file`.

Рекомендуемый лимит:

```yaml
logging:
  driver: json-file
  options:
    max-size: "50m"
    max-file: "5"
```

Итоговый лимит на один контейнер: до 250 MB логов. После достижения лимита Docker удаляет самые старые файлы.

## 6. Alert rules

Основные правила:

| Alert | Severity | Условие |
| --- | --- | --- |
| `InstanceDown` | critical | `node-exporter` недоступен больше 1 минуты |
| `DiskSpaceLow` | warning | На `/` осталось меньше 10% свободного места 5 минут |
| `HighCpuLoad` | warning | CPU load выше 90% 5 минут |
| `ContainerDown` | critical | Docker-контейнер stopped дольше 1 минуты |

Пример:

```yaml
groups:
  - name: backuphub
    rules:
      - alert: DiskSpaceLow
        expr: (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) * 100 < 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Low disk space on {{ $labels.server }}"
          description: "Root filesystem has less than 10% free space."
```

## 7. Alertmanager

Alertmanager группирует алерты и отправляет их в Telegram.

Ключевые настройки:

```yaml
route:
  group_by: ["alertname", "server"]
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
```

Смысл настроек:

- `group_by` объединяет алерты по имени и серверу;
- `group_wait` ждет 10 секунд перед первой отправкой, чтобы собрать похожие алерты;
- `group_interval` задает частоту отправки новых алертов в уже существующей группе;
- `repeat_interval` повторяет нерешенную проблему раз в час;
- `send_resolved: true` включает уведомления о восстановлении.

Telegram bot token и chat id считаются секретами и не хранятся в git.

## 8. Grafana dashboards

Основные dashboards:

- hosts metrics на основе Node Exporter;
- containers metrics на основе cAdvisor;
- logs dashboard на основе Loki;
- infrastructure availability;
- backup freshness после внедрения регулярных backup jobs.

В логовом dashboard должны быть фильтры:

- `server`;
- `container`;
- `service_name`;
- `log_source`.

Для поиска 5xx по Nginx:

```logql
{server=~"$server", log_source="nginx"} |= " 5"
```

Для ошибок приложения:

```logql
{server=~"$server", container=~"$container"} |~ "(?i)error|exception|traceback|failed"
```

## 9. Retention

Retention должен быть ограничен, потому что серверы маленькие по диску.

Рекомендуемая политика:

| Хранилище | Retention |
| --- | --- |
| Prometheus | 15-30 дней |
| Loki | 7-14 дней |
| Docker container logs | `max-size=50m`, `max-file=5` |

Точные значения retention должны соответствовать свободному месту на `infra`.

## 10. Проверочные команды

Prometheus targets:

```bash
curl -I https://prometheus.backuphub.spb.ru
```

Loki readiness внутри infra:

```bash
curl -fsS http://loki:3100/ready
```

Alloy logs:

```bash
docker logs --tail=200 grafana-alloy
```

cAdvisor labels:

```bash
curl -fsS https://cadvisor.dev.backuphub.spb.ru/metrics | grep compose_project | head
```

## 11. Инциденты

Пошаговые действия описаны в [RUNBOOK.md](RUNBOOK.md).

PR, меняющий alert rules, Grafana dashboards, Loki/Alloy, Prometheus scrape config или Alertmanager routing, должен обновлять этот документ.
