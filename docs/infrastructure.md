# BackupHub. Инфраструктура

Документ описывает инфраструктуру BackupHub и дополняет схемы из [main.drawio](main.drawio).

Важно: BackupHub **не выполняет резервное копирование внешних систем и не хранит их архивы**. Он хранит метаданные: систему, сервер, статус, время, размер, ошибку и технический JSON.

MinIO в этой инфраструктуре используется отдельно: **для хранения бэкапов собственной PostgreSQL БД BackupHub**.

## Содержание

- [1. Схемы](#1-схемы)
- [2. Серверы](#2-серверы)
- [3. Общая логика](#3-общая-логика)
- [4. DEV и PROD](#4-dev-и-prod)
- [5. INFRA](#5-infra)
- [6. Контейнеры](#6-контейнеры)
- [7. Сетевые потоки](#7-сетевые-потоки)
- [8. CI/CD](#8-cicd)
- [9. Хранение данных](#9-хранение-данных)
- [10. Бэкапы PostgreSQL в MinIO](#10-бэкапы-postgresql-в-minio)
- [11. Порты](#11-порты)
- [12. Безопасность](#12-безопасность)
- [13. Мониторинг](#13-мониторинг)

## 1. Схемы

Основная редактируемая схема:

- [main.drawio](main.drawio)

PNG-версия схемы для быстрого просмотра:

![BackupHub infrastructure](infrastructure-overview.png)


## 2. Серверы

Инфраструктура состоит из трех машин:

| Сервер | Hostname | Назначение |
| --- | --- | --- |
| `dev` | `dev.backuphub.spb.ru` | Тестовый контур. Сюда попадают изменения из ветки `DEV`, здесь выполняются сборка, тесты и запуск обновленного Docker Compose |
| `prod` | `prod.backuphub.spb.ru` | Боевой контур. Принимает реальные данные от backup-инструментов и обслуживает пользователей |
| `infra` | `infra.backuphub.spb.ru` | Инфраструктурный контур. Хранит мониторинг, логи, алерты и бэкапы PostgreSQL БД BackupHub |

Параметры серверов:

| Параметр | `dev` | `prod` | `infra` |
| --- | --- | --- | --- |
| IP | `130.49.129.180/24` | `153.80.184.132/24` | `78.17.144.232/24` |
| ОС | Ubuntu 22.04.5 LTS | Ubuntu 22.04.2 LTS | Ubuntu 24.04 LTS |
| SSH порт | `8228` | `8228` | `8228` |
| RAM | 1 GB | 1 GB | 2 GB |
| Диск | 15 GB ext4 | 15 GB ext4 | 15 GB ext4 |


## 3. Общая логика

BackupHub работает как web/API-приложение. При обращении через REST API передает сведения об операции: система, сервер, время начала и завершения, статус, размер backup, ошибка при падении и дополнительные технические данные.


## 4. DEV и PROD

`dev` и `prod` похожи по составу контейнеров. На обоих серверах работают Nginx, Django / DRF, Celery Worker, Celery Beat, Flower, Redis, PostgreSQL, Certbot, Promtail, Node Exporter и cAdvisor.

Разница между `dev` и `prod` не столько в составе, сколько в режиме эксплуатации.

| Область | DEV | PROD |
| --- | --- | --- |
| Назначение | Проверка изменений | Боевая эксплуатация |
| Git ref | `DEV` | `PROD` |
| Deploy | После merge в `DEV` | После approval |
| Данные | Тестовые или неполные | Реальные production-данные |
| Backup БД | Обязателен | Обязателен |
| Settings | Допускается мягче | `DEBUG=False`, строгие hosts/secrets |


## 5. INFRA

`infra` не обслуживает пользовательские HTTP-запросы BackupHub. Он отвечает за сбор метрик, хранение логов, дашборды, алерты и хранение бэкапов PostgreSQL БД BackupHub.

Контейнеры `infra`:

| Контейнер | Назначение |
| --- | --- |
| Prometheus | Сбор и хранение метрик |
| Grafana | Дашборды и Explore |
| Loki | Хранилище логов |
| Alertmanager | Маршрутизация алертов |
| MinIO | S3-compatible storage для бэкапов PostgreSQL |
| Node Exporter | Метрики infra-хоста |
| cAdvisor | Метрики infra-контейнеров |
| Grafana Alloy | Отправка infra-логов в Loki |


## 6. Контейнеры

### DEV / PROD

| Контейнер | Порт | Назначение |
| --- | --- | --- |
| Nginx | `80`, `443` | Публичная точка входа, reverse proxy |
| Django / DRF | `8000` internal | Web UI, REST API, Swagger/ReDoc |
| PostgreSQL 16 | `5432` internal | Основная БД BackupHub |
| Redis | `6379` internal | Celery broker и result backend |
| Celery Worker | internal | Выполнение фоновых задач |
| Celery Beat | internal | Периодические задачи |
| Flower | `5555` internal/admin | UI для Celery |
| Certbot | internal | Let's Encrypt сертификаты |
| Grafanf Alloy | `12345` internal | Отправка логов в Loki |
| Node Exporter | `9100` infra/admin | Метрики ОС |
| cAdvisor | `8080` infra/admin | Метрики контейнеров |

### INFRA

| Контейнер | Порт | Назначение |
| --- | --- | --- |
| Prometheus | `9090` | Метрики и alert rules |
| Grafana | `3000` | Дашборды |
| Loki | `3100` | Логи |
| Alertmanager | `9093` | Уведомления, например Telegram |
| MinIO | `9000`, `9001` | Бэкапы PostgreSQL БД BackupHub |
| Node Exporter | `9100` | Метрики infra-сервера |
| cAdvisor | `8080` | Метрики infra-контейнеров |
| Grafanf Alloy | `12345` | Отправка infra-логов |

## 7. Сетевые потоки

### Web/API

```text
Internet
  -> Nginx :443
  -> Django :8000
  -> PostgreSQL :5432
```

Nginx завершает TLS и проксирует запросы в Django. Django не должен быть доступен напрямую извне.

### Flower

```text
Nginx
  -> /flower/
  -> Flower :5555
```

Flower показывает состояние Celery. На production доступ к Flower должен быть закрыт для публичного интернета.

### Celery

```text
Django / Beat
  -> Redis :6379
  -> Worker
  -> PostgreSQL :5432
```

Redis используется как очередь задач и backend результатов. Celery Worker выполняет задачи и при необходимости пишет данные в PostgreSQL.

### Logs

```text
Grafana Alloy на dev/prod/infra
  -> Loki на infra :3100
```

Grafanf Alloy читает Docker logs, Nginx logs и system logs.

### Metrics

```text
Prometheus на infra
  -> Node Exporter :9100
  -> cAdvisor :8080
```

Prometheus работает по pull-модели: он сам забирает метрики с `dev`, `prod` и `infra`.

## 8. CI/CD

Docker Registry в текущей архитектуре отсутствует. Образ собирается прямо на том сервере, где должен запускаться контейнер.

### DEV flow

```text
Pull Request
  -> GitHub Actions checks
  -> merge to dev
  -> GitHub Runner на dev
  -> checkout / pull
  -> docker compose build
  -> automated tests
  -> docker compose up -d --build
  -> cleanup old images/cache
```

GitHub Runner на `dev` работает как systemd service. Он не является контейнером и управляет Docker Engine на сервере.

### PROD flow

```text
release branch / tag / main
  -> protected GitHub environment
  -> manual approval
  -> runner/deploy на prod
  -> backup PostgreSQL в MinIO
  -> docker compose build
  -> migrations
  -> docker compose up -d
  -> smoke check
  -> cleanup old images/cache
```

Production deploy должен идти только после проверки на `dev`. Перед production-миграциями обязательно нужен свежий backup PostgreSQL.

## 9. Хранение данных

### PostgreSQL

PostgreSQL - основное долговременное хранилище BackupHub. В нем находятся наблюдаемые системы, зарегистрированные серверы, API keys, операции резервного копирования, статусы, время начала и завершения, размер, ошибки, технические данные и служебные Django-таблицы.

Volume:

```text
postgres_data
/opt/backuphub/data/postgres -> /var/lib/postgresql/data
```

Этот volume нельзя удалять.

### Redis

Redis используется для Celery. В нем находятся очередь задач, результаты задач и временное состояние фоновых процессов.

Volume:

```text
redis_data
/opt/backuphub/data/redis -> /data
```

Redis не является основным бизнес-хранилищем. Потеря Redis не должна уничтожить историю BackupHub.

### INFRA volumes

| Volume | Назначение |
| --- | --- |
| `prometheus_data` | История метрик |
| `grafana_data` | Dashboards, datasources, users |
| `loki_data` | Логи |
| `alertmanager_data` | Silences и notification log |
| `minio_data` | Бэкапы PostgreSQL БД BackupHub |

Все эти volumes являются stateful, их нельзя удалять автоматической очисткой.

## 10. Бэкапы PostgreSQL в MinIO

MinIO используется для хранения бэкапов собственной PostgreSQL БД BackupHub. MinIO не хранит архивы внешних систем.

Целевая модель:

```text
DB backup job
  -> WAL-G / pg_dump
  -> base backup + WAL archive
  -> MinIO S3 API :9000
  -> bucket backuphub-postgres-backups
```

На схеме backup job показан рядом с PostgreSQL: он читает данные PostgreSQL и загружает backup в MinIO через S3 API.

Что обязательно: backup production PostgreSQL перед миграциями, регулярный backup по расписанию, retention для старых бэкапов, отдельный MinIO access key для backup job, запрет хранения MinIO credentials в git и периодическая проверка restore.

Backup без проверки восстановления нельзя считать рабочим.

## 11. Порты

### Публичные порты

| Сервер | Порт | Назначение |
| --- | --- | --- |
| `dev` | `80`, `443` | HTTP/HTTPS приложения |
| `prod` | `80`, `443` | HTTP/HTTPS приложения |
| `dev/prod/infra` | `8228` | SSH только для админов |

### Внутренние и административные порты

| Порт | Сервис | Доступ |
| --- | --- | --- |
| `8000` | Django | Только Docker Compose / Nginx |
| `5555` | Flower | Только admin/VPN |
| `5432` | PostgreSQL | Только Docker Compose |
| `6379` | Redis | Только Docker Compose |
| `12345` | Grafanf Alloy | Только local/internal |
| `9100` | Node Exporter | Только Prometheus/admin |
| `8080` | cAdvisor | Только Prometheus/admin |
| `3100` | Loki | Только Promtail/admin |
| `9090` | Prometheus | Только admin/VPN |
| `9093` | Alertmanager | Только admin/VPN |
| `3000` | Grafana | Только admin/VPN или HTTPS reverse proxy |
| `9000` | MinIO API | Только admin/VPN и DB backup jobs |
| `9001` | MinIO Console | Только admin/VPN |

## 12. Безопасность

### SSH

SSH перенесен со стандартного порта `22` на `8228`.

Базовая политика:

```text
Port 8228
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
PermitEmptyPasswords no
X11Forwarding no
```

Требования:

- вход только по SSH-ключам;
- вход по паролю запрещен;
- вход под `root` запрещен;
- у каждого администратора свой ключ;
- общие ключи не используются;
- runner/deploy user не используется для ручной работы;
- после изменения `sshd_config` выполняется `sshd -t`;


### Firewall

В интернет можно открывать только минимально необходимые порты. Для `dev` и `prod` публичны только `80`, `443` и `8228` для администраторов. Для `infra` admin-интерфейсы должны быть доступны только через admin IP/VPN.

Нельзя открывать в интернет PostgreSQL `5432`, Redis `6379`, Django `8000`, Flower `5555`, Prometheus `9090`, Loki `3100`, Alertmanager `9093`, MinIO `9000/9001`, Node Exporter `9100`, cAdvisor `8080` и Docker socket/API.

### Secrets

Секреты не должны храниться в git. К секретам относятся Django `SECRET_KEY`, PostgreSQL password, Redis password, Flower basic auth, MinIO root credentials, MinIO access key для backup jobs, Telegram bot token, GitHub runner token и SSH private keys.

Для `dev` и `prod` должны использоваться разные секреты.

## 13. Мониторинг

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
- ошибки Promtail / Loki;
- заполнение диска на `infra`.

Alertmanager отправляет алерты в Telegram. Grafana используется для просмотра дашбордов, анализа метрик, поиска по логам, диагностики инцидентов и проверки состояния после deploy.

### 1. Правила мониторинга (alert.rules.yml)
Этот файл отвечает за генерацию алертов при достижении критических показателей:

* **InstanceDown (Критический):** Срабатывает, если агент `node-exporter` (сборщик метрик системы) недоступен более **1 минуты**. Это означает, что сервер либо выключен, либо на нем упал сервис мониторинга.
* **DiskSpaceLow (Предупреждение):** Срабатывает, если на корневом разделе (`/`) осталось **менее 10% свободного места** на протяжении **5 минут**.
* **HighCpuLoad (Предупреждение):** Срабатывает, если средняя нагрузка на процессор (CPU) превышает **90%** в течение **5 минут**.
* **ContainerDown (Критический):** Срабатывает, если какой-либо Docker-контейнер перешел в состояние `stopped` (остановлен) и находится в нем дольше **1 минуты**.

### 2. Правила обработки и отправки (alertmanager.yml)
Этот файл определяет, куда и с какой частотой отправляются созданные алерты:

* **Группировка:** Алерты объединяются в одно сообщение по совпадению имени ошибки (`alertname`) и сервера (`server`). Это защищает от флуда, если на одном хосте упало сразу несколько связанных вещей.
* **Тайминги:**
  * `group_wait: 10s` — при появлении первого алерта система ждет 10 секунд, чтобы собрать другие похожие алерты в одну группу перед отправкой.
  * `group_interval: 10s` — новые алерты в уже существующей группе отправляются с интервалом в 10 секунд.
  * `repeat_interval: 1h` — если авария не устранена, повторное напоминание в чат придет ровно через 1 час.
* **Канал отправки:** Все уведомления уходят в Telegram-чат через указанного бота (ID чата скрыт).
* **Уведомления о восстановлении:** Включена опция `send_resolved: true` — когда сервер или контейнер починится, в чат придет сообщение с пометкой **[RESOLVED]**.
* **Шаблон сообщения:** Настроен красивый HTML-вывод, который выводит статус (ALERT/RESOLVED), имя хоста, окружение, имя алерта, его критичность, описание и точное время старта проблемы.

