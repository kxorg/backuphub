# BackupHub. Runbook

Документ описывает действия при типовых инцидентах. Цель - снизить MTTR и дать понятные шаги человеку, который впервые дежурит по проекту.

## 1. Первичная диагностика

Всегда начать с трех вопросов:

1. Что недоступно: приложение, БД, мониторинг, deploy, runner?
2. На каком сервере проблема: `dev`, `prod`, `infra`, `secops`?
3. Это падение сервиса, нехватка ресурсов, сеть/TLS или ошибка deploy?

Базовые команды:

```bash
hostname
df -h
free -m
uptime
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
docker system df
```

Логи Docker:

```bash
docker logs --tail=200 <container_name>
```

Compose status:

```bash
docker compose ps
docker compose logs --tail=200
```

## 2. Приложение отдает 502

Симптомы:

- `https://dev.backuphub.spb.ru` или `https://prod.backuphub.spb.ru` возвращает `502 Bad Gateway`;
- Nginx жив, но upstream недоступен.

Проверка:

```bash
cd /opt/backuphub/app
docker compose -f deploy.docker-compose.yml ps
docker logs --tail=200 app_DEV
```

Проверить Nginx:

```bash
cd /opt/backuphub/infra
docker compose ps
docker logs --tail=200 nginx
```

Проверить, что app-контейнер слушает `8000` внутри Docker-сети:

```bash
docker exec -it nginx sh
curl -v http://app_DEV:8000/
```

Решение:

```bash
cd /opt/backuphub/app
docker compose -f deploy.docker-compose.yml up -d --build
docker logs --tail=200 app_DEV
```

Если ошибка после deploy, смотреть [DEPLOYMENT.md](DEPLOYMENT.md) и откатываться на предыдущий commit/image.

## 3. PostgreSQL упал

Симптомы:

- приложение возвращает 500;
- в логах `connection refused`, `could not connect to server`, `database is not accepting connections`;
- контейнер PostgreSQL stopped/unhealthy.

Проверка:

```bash
cd /opt/backuphub/database
docker compose ps
docker logs --tail=200 postgres
```

Проверить подключение:

```bash
docker exec -it postgres pg_isready -U "$POSTGRES_USER"
```

Решение:

```bash
cd /opt/backuphub/database
docker compose up -d postgres
docker logs --tail=200 postgres
```

Если данные повреждены:

1. Не удалять volume.
2. Остановить приложение.
3. Сделать копию текущего volume/данных.
4. Восстановить из backup по [BACKUPS.md](BACKUPS.md).

## 4. Redis упал

Симптомы:

- Celery не принимает задачи;
- Flower не показывает workers;
- в логах `redis connection refused`.

Проверка:

```bash
cd /opt/backuphub/database
docker compose ps
docker logs --tail=200 redis
```

Решение:

```bash
cd /opt/backuphub/database
docker compose up -d redis
cd /opt/backuphub/app
docker compose -f deploy.docker-compose.yml restart celery_worker celery_beat flower
```

Redis не является основным бизнес-хранилищем. Потеря Redis не должна уничтожить историю BackupHub.

## 5. Диск забит

Симптомы:

- Alert `DiskSpaceLow`;
- runner перестал подхватывать code/deploy;
- Docker build падает с ошибками записи;
- приложения пишут `No space left on device`.

Проверка:

```bash
df -h
du -xh / --max-depth=1 2>/dev/null | sort -h
docker system df
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Size}}"
```

Проверить Docker:

```bash
docker image ls
docker builder du
```

Безопасная очистка dangling images:

```bash
docker image prune -f
```

Очистка build cache:

```bash
docker builder prune -af
```

Очистка старых stopped containers:

```bash
docker container prune -f
```

Журналы systemd:

```bash
journalctl --disk-usage
journalctl --vacuum-size=500M
```

Не удалять:

- PostgreSQL volume;
- MinIO data;
- Grafana/Loki/Prometheus volumes без согласования;
- Vaultwarden data.

## 6. OOM-killer убил контейнер

Симптомы:

- контейнер внезапно restarted;
- exit code `137`;
- в GitHub Actions тесты падают с `Process completed with exit code 137`.

Проверка:

```bash
dmesg -T | grep -i -E "killed process|oom"
docker inspect <container_name> --format '{{.State.OOMKilled}} {{.State.ExitCode}}'
```

Решение:

- уменьшить набор контейнеров в тестовом compose;
- убрать лишние сервисы из CI;
- проверить memory limits;
- запускать тесты без лишних процессов;
- для GitHub-hosted runner использовать `test.docker-compose.yml`, а не полный local/deploy compose.

## 7. TLS-сертификат истек

Симптомы:

- браузер показывает ошибку сертификата;
- `curl` падает с TLS error;
- Prometheus не может scrape HTTPS endpoint.

Проверка:

```bash
openssl s_client -connect dev.backuphub.spb.ru:443 -servername dev.backuphub.spb.ru </dev/null 2>/dev/null | openssl x509 -noout -dates
```

Renew dry-run:

```bash
cd /opt/backuphub/infra
docker compose run --rm certbot renew --dry-run
```

Перевыпуск сертификата для набора доменов:

```bash
docker compose run --rm certbot certonly \
  --webroot \
  -w /var/www/certbot \
  -d example.backuphub.spb.ru \
  --register-unsafely-without-email
```

После выпуска:

```bash
docker compose restart nginx
```

## 8. GitHub Runner не отвечает

Симптомы:

- job висит в `Waiting for a runner to pick up this job`;
- runner в GitHub UI offline;
- deploy не стартует после merge.

Проверка на сервере:

```bash
systemctl list-units "*runner*"
systemctl status "<runner-service-name>"
journalctl -u "<runner-service-name>" -n 200 --no-pager
```

Проверить диск:

```bash
df -h
docker system df
```

Проверить labels в workflow:

```yaml
runs-on: [self-hosted, dev]
```

Labels в workflow должны совпадать с labels runner в GitHub organization/repository settings.

Решение:

```bash
sudo systemctl restart "<runner-service-name>"
```

Если причина в диске, выполнить очистку из раздела "Диск забит".

## 9. Prometheus не собирает метрики

Симптомы:

- target down в Prometheus;
- Grafana panels пустые;
- нет `node-exporter`/`cadvisor` series.

Проверка с `infra`:

```bash
curl -vk https://node-exporter.dev.backuphub.spb.ru/metrics
curl -vk https://cadvisor.dev.backuphub.spb.ru/metrics
```

Проверить firewall на target-сервере:

```bash
sudo iptables -L ufw-user-input -n -v
sudo ufw status numbered
```

Проверить контейнеры:

```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

Решение:

- убедиться, что `infra` IP разрешен;
- проверить Nginx endpoint;
- проверить, что Node Exporter/cAdvisor запущены;
- проверить Prometheus scrape config.

## 10. Loki не принимает логи

Симптомы:

- в Grafana Explore нет labels;
- Alloy пишет ошибки отправки;
- Loki endpoint недоступен.

Проверка на `infra`:

```bash
docker logs --tail=200 loki
curl -fsS http://loki:3100/ready
```

Проверка Alloy:

```bash
docker logs --tail=200 grafana-alloy
```

Проверка endpoint:

```bash
curl -I https://infra.backuphub.spb.ru/loki/api/v1/push
```

Решение:

- проверить allowlist IP;
- проверить Nginx location `/loki/api/v1/push`;
- перезапустить Alloy после изменения config;
- проверить свободное место на `infra`.

## 11. MinIO недоступен

Симптомы:

- backup job не может загрузить dump;
- `minio.backuphub.spb.ru` или `s3.backuphub.spb.ru` недоступен.

Проверка:

```bash
cd /opt/backuphub/infra
docker compose ps
docker logs --tail=200 minio
docker logs --tail=200 nginx
```

Решение:

```bash
docker compose up -d minio nginx
```

Если поврежден volume, перед любыми действиями сделать копию `minio_data`.

## 12. Контакты эскалации

Порядок:

1. Ответственный за инфраструктуру.
2. Backend/DevOps lead.
3. Руководитель проекта.

Актуальные контакты и телефоны должны быть в закрепленном сообщении командного Telegram-чата.

## 13. После инцидента

После восстановления:

1. Зафиксировать причину.
2. Зафиксировать команды, которые помогли.
3. Проверить, нужен ли новый alert.
4. Обновить runbook, если инструкции были неполными.
5. Сообщить команде статус и остаточные риски.
