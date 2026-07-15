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
- [8. Nginx и внешние endpoints](#8-nginx-и-внешние-endpoints)
- [9. CI/CD](#9-cicd)
- [10. Хранение данных](#10-хранение-данных)
- [11. Бэкапы PostgreSQL в MinIO](#11-бэкапы-postgresql-в-minio)
- [12. Порты](#12-порты)
- [13. Безопасность](#13-безопасность)
- [14. Мониторинг](#14-мониторинг)

## 1. Схемы

Основная редактируемая схема:


- [main.drawio](main.drawio)

PNG-версия схемы для быстрого просмотра:

![BackupHub infrastructure](infrastructure-overview.png)

Дополнительные схемы:

![CI/CD до внедрения SecOps](ci-cd-before-secops.png)

![CI/CD после внедрения SecOps](ci-cd-after-secops.png)

![GitHub runners](github-runners.png)


## 2. Серверы

Инфраструктура состоит из трех машин:


| Параметр | `dev` | `prod` | `infra` | `secops` |
| :--- | :--- | :--- | :--- | :--- |
| **Hostname** | `dev.backuphub.spb.ru` | `prod.backuphub.spb.ru` | `infra.backuphub.spb.ru` | `secops.backuphub.spb.ru` |
| **Назначение** | Тестовый контур. Сюда попадают изменения из ветки `DEV`, здесь выполняются сборки. | Боевой контур. Принимает реальные данные от backup-инструментов и обслуживает пользователей. | Инфраструктурный контур. Хранит мониторинг, логи, алерты и бэкапы PostgreSQL. | Безопасность и аудит (SecOps). Анализ уязвимостей, управление секретами и контроль доступа. |
| **Тариф / Локация** | Lite (Россия) | Lite (Россия) | Promo (Финляндия) | Lite (Россия) |
| **IP-адрес** | `130.49.129.180/24` | `153.80.184.132/24` | `78.17.144.232/24` | `157.22.230.253/24` |
| **ОС** | Ubuntu 22.04.5 LTS | Ubuntu 22.04.2 LTS | Ubuntu 24.04 LTS | Ubuntu 22.04 LTS *(предположительно)* |
| **SSH порт** | `8228` | `8228` | `8228` | `8228` *(предположительно)* |
| **RAM** | 1 GB | 1 GB | 2 GB | 1 GB |
| **Диск** | 15 GB ext4 | 15 GB ext4 | 15 GB ext4 | 15 GB ext4 |
| **Оплачен до** | 2026-08-02 | 2026-08-02 | 2026-08-02 | 2026-08-13 |


## 3. Общая логика
BackupHub работает как web/API-приложение. При обращении через REST API передает сведения об операции: система, сервер, время начала и завершения, статус, размер backup, ошибка при падении и дополнительные технические данные.


## 4. DEV и PROD

`dev` и `prod` похожи по составу контейнеров. На обоих серверах работают Nginx, Django / DRF, Celery Worker, Celery Beat, Flower, Redis, PostgreSQL, Certbot, Grafana Alloy, Node Exporter и cAdvisor.

Разница между `dev` и `prod` не столько в составе, сколько в режиме эксплуатации.

| Область | DEV | PROD |
| --- | --- | --- |
| Назначение | Проверка изменений | Боевая эксплуатация |
| Git ref | `DEV` | `PROD` |
| Deploy | После merge в `DEV` | После approval |
| Данные | Тестовые или неполные | Реальные production-данные |
| Backup БД | Обязателен | Обязателен |
| Settings | Допускается мягче | `DEBUG=False`, строгие hosts/secrets |

На `dev` и `prod` приложение, база и инфраструктурные агенты разделены по разным директориям и compose-файлам:

| Директория | Что запускает | Почему отдельно |
| --- | --- | --- |
| `/opt/backuphub/app` | Django / DRF и связанные app-контейнеры | CI/CD пересобирает именно приложение |
| `/opt/backuphub/database` | PostgreSQL и Redis | БД не пересоздается при каждом deploy приложения |
| `/opt/backuphub/infra` | Nginx, Certbot, Node Exporter, cAdvisor, Grafana Alloy | Инфраструктурные сервисы живут отдельно от app-deploy |

Все compose-файлы подключены к общей Docker-сети `backuphub_network`. За счет этого Nginx из infra-compose может проксировать запросы в app-compose, а приложение может обращаться к PostgreSQL и Redis.


## 5. INFRA

`infra` не обслуживает пользовательские HTTP-запросы BackupHub. Он отвечает за сбор метрик, хранение логов, дашборды, алерты и хранение бэкапов PostgreSQL БД BackupHub.

На `infra` также работает Nginx. Он является единственной публичной HTTPS-точкой входа для инфраструктурных web-интерфейсов и для приема логов в Loki.

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
| Nginx | HTTPS reverse proxy для UI и Loki ingest endpoint |
| Certbot | Выпуск и обновление TLS-сертификатов |
| Vaultwarden | Внутреннее хранилище секретов команды |


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
| Grafana Alloy | `12345` internal | Читает Docker/Nginx/system logs и отправляет их в Loki |
| Node Exporter | `9100` internal | Метрики ОС; наружу не публикуется напрямую |
| cAdvisor | `8080` internal | Метрики контейнеров; наружу не публикуется напрямую |

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
| Grafana Alloy | `12345` | Отправка infra-логов |
| Nginx | `80`, `443` | HTTPS reverse proxy для Grafana, Prometheus, Alertmanager, MinIO, Vaultwarden и Loki ingest |
| Certbot | internal | Let's Encrypt сертификаты |
| Vaultwarden | `80` internal | Web UI и API хранилища секретов |

## 7. Сетевые потоки

### Web/API

```text
Internet
  -> dev/prod Nginx :443
  -> app_DEV/app_PROD :8000
  -> PostgreSQL :5432
```

Nginx завершает TLS, выполняет HTTP -> HTTPS redirect и проксирует запросы в Django. Django не должен быть доступен напрямую извне.

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
  -> https://infra.backuphub.spb.ru/loki/api/v1/push
  -> infra Nginx :443
  -> Loki :3100
```

Grafana Alloy читает Docker logs, Nginx logs и system logs. Для отправки логов используется отдельный nginx endpoint Loki:

```text
/loki/api/v1/push
```

Эта ручка предназначена только для приема логов от Alloy. Она не является публичным UI. Доступ к ней должен быть ограничен allowlist по IP серверов `dev`, `prod` и `infra`.

### Metrics

```text
Prometheus на infra
  -> https://node-exporter.dev.backuphub.spb.ru/metrics
  -> https://cadvisor.dev.backuphub.spb.ru/metrics
  -> https://node-exporter.prod.backuphub.spb.ru/metrics
  -> https://cadvisor.prod.backuphub.spb.ru/metrics
  -> node-exporter:9100 на infra
  -> cadvisor:8080 на infra
```

Prometheus работает по pull-модели: он сам забирает метрики с `dev`, `prod` и `infra`.

На `dev` и `prod` Node Exporter и cAdvisor спрятаны за локальным Nginx. Прямые порты `9100` и `8080` наружу не публикуются. Nginx отдает их по отдельным HTTPS-поддоменам и должен пропускать только IP `infra`, где работает Prometheus.

Метрики cAdvisor собираются с labels:

```text
node=dev|prod|infra
server=dev|prod|infra
container=<docker container name>
service=<docker compose service>
compose_project=<docker compose project>
```

Эти labels используются в Grafana dashboard для фильтрации по серверам и контейнерам.

## 8. Nginx и внешние endpoints

Во внешнюю сеть у серверов смотрят только `80`, `443` и SSH `8228`. Все web-интерфейсы и технические endpoints должны идти через Nginx.

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
| `https://s3.backuphub.spb.ru` | `minio:9000` | Для backup jobs, без browser UI |
| `https://vaultwarden.backuphub.spb.ru` | `vaultwarden:80` | Аутентификация Vaultwarden |
| `https://infra.backuphub.spb.ru/loki/api/v1/push` | `loki:3100/loki/api/v1/push` | IP allowlist для Alloy |

Для Vaultwarden не используется общая Nginx Basic Auth на весь сайт, чтобы не ломать web-клиент, приглашения и мобильные клиенты. Защита выполняется средствами Vaultwarden: master password, admin token, запрет свободной регистрации после onboarding команды.

## 9. CI/CD

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

## 10. Хранение данных

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

## 11. Бэкапы PostgreSQL в MinIO

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

## 12. Порты

### Публичные порты

| Сервер | Порт | Назначение |
| --- | --- | --- |
| `dev` | `80`, `443` | HTTP/HTTPS приложения и protected metrics endpoints через Nginx |
| `prod` | `80`, `443` | HTTP/HTTPS приложения и protected metrics endpoints через Nginx |
| `infra` | `80`, `443` | HTTPS reverse proxy для monitoring UI, MinIO, Vaultwarden и Loki ingest |
| `dev/prod/infra` | `8228` | SSH только для админов |

### Внутренние и административные порты

| Порт | Сервис | Доступ |
| --- | --- | --- |
| `8000` | Django | Только Docker Compose / Nginx |
| `5555` | Flower | Только admin/VPN |
| `5432` | PostgreSQL | Только Docker Compose |
| `6379` | Redis | Только Docker Compose |
| `12345` | Grafana Alloy | Только local/internal |
| `9100` | Node Exporter | Не публикуется напрямую; доступ через Nginx metrics endpoint |
| `8080` | cAdvisor | Не публикуется напрямую; доступ через Nginx metrics endpoint |
| `3100` | Loki | Не публикуется напрямую; ingest через `/loki/api/v1/push` на infra Nginx |
| `9090` | Prometheus | Не публикуется напрямую; UI через infra Nginx |
| `9093` | Alertmanager | Не публикуется напрямую; UI через infra Nginx |
| `3000` | Grafana | Не публикуется напрямую; UI через infra Nginx |
| `9000` | MinIO API | Не публикуется напрямую; S3 API через `s3.backuphub.spb.ru` |
| `9001` | MinIO Console | Не публикуется напрямую; UI через `minio.backuphub.spb.ru` |

## 13. Безопасность

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

В интернет можно открывать только минимально необходимые порты. Для `dev`, `prod` и `infra` публичны только `80`, `443` и `8228` для администраторов.

Нельзя открывать в интернет PostgreSQL `5432`, Redis `6379`, Django `8000`, Flower `5555`, Prometheus `9090`, Loki `3100`, Alertmanager `9093`, MinIO `9000/9001`, Node Exporter `9100`, cAdvisor `8080` и Docker socket/API.

Для административных web-интерфейсов используется Nginx:

- Grafana, Prometheus, Alertmanager и MinIO Console закрываются Nginx Basic Auth;
- Node Exporter и cAdvisor доступны только Prometheus с IP `infra`;
- Loki ingest endpoint `/loki/api/v1/push` доступен только Alloy с разрешенных IP;
- Vaultwarden не закрывается общей Basic Auth, потому что использует собственную аутентификацию и клиентские протоколы;
- прямой доступ к внутренним портам контейнеров должен быть закрыт Docker Compose `expose` и firewall/iptables.

### Secrets

Секреты не должны храниться в git. К секретам относятся Django `SECRET_KEY`, PostgreSQL password, Redis password, Flower basic auth, MinIO root credentials, MinIO access key для backup jobs, Telegram bot token, GitHub runner token и SSH private keys.

Для `dev` и `prod` должны использоваться разные секреты.

## 14. Мониторинг

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
- заполнение диска на `infra`.

Alertmanager отправляет алерты в Telegram. Grafana используется для просмотра дашбордов, анализа метрик, поиска по логам, диагностики инцидентов и проверки состояния после deploy.

cAdvisor обновлен до образа `ghcr.io/google/cadvisor:v0.57.0` и запускается с доступом к Docker socket. Это нужно, чтобы Prometheus видел не только systemd/cgroup-метрики, но и нормальные Docker labels: `container`, `service`, `compose_project`, `node`.

Для контейнерного мониторинга используется Grafana dashboard на основе cAdvisor. Основные фильтры: `node`, `job`, `service`, `container`.

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

Для всех контейнеров установлены следующие лимиты:
* **Драйвер логирования:** `json-file` (стандартный для Docker).
* **Максимальный размер одного файла (`max-size`):** `50m` (50 Мегабайт).
* **Глубина хранения (`max-file`):** `5` файлов.
* **Лимит на один контейнер:** максимум **250 МБ** (5 файлов $\times$ 50 МБ). По достижении лимита Docker автоматически удаляет самые старые записи и перезаписывает файлы по кругу.
