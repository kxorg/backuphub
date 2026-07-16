# BackupHub. Security

Документ описывает текущую политику безопасности серверов и инфраструктурных сервисов.

Аудитория: DevOps, лид, аудиторы.

## 1. Базовая модель

VPN сейчас не используется. Ограничение доступа выполняется через:

- SSH hardening;
- UFW/iptables;
- Nginx reverse proxy;
- Nginx Basic Auth для административных UI;
- IP allowlist для метрик и Loki ingest;
- встроенную авторизацию сервисов, например Grafana, MinIO, Vaultwarden.

Публичная поверхность серверов должна быть минимальной:

```text
80/tcp   HTTP, redirect и Let's Encrypt challenge
443/tcp  HTTPS
8228/tcp SSH для администраторов
```

## 2. SSH

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
- после изменения `sshd_config` выполняется проверка `sshd -t`.

Проверка:

```bash
sudo sshd -t
sudo ss -tulpen | grep 8228
```

## 3. Firewall

Для `dev`, `prod`, `infra`, `secops` публично разрешаются только минимально необходимые порты.

Нельзя открывать в интернет:

- PostgreSQL `5432`;
- Redis `6379`;
- Django `8000`;
- Flower `5555`;
- Prometheus `9090`;
- Loki `3100`;
- Alertmanager `9093`;
- MinIO `9000/9001`;
- Node Exporter `9100`;
- cAdvisor `8080`;
- Docker socket/API.

Проверка UFW:

```bash
sudo ufw status verbose
sudo ufw status numbered
```

Проверка iptables:

```bash
sudo iptables -L INPUT -n -v
sudo iptables -L ufw-user-input -n -v
sudo iptables -L DOCKER-USER -n -v
```

Ожидаемая модель для `dev/prod`:

```text
ACCEPT tcp dpt:8228 from 0.0.0.0/0
ACCEPT tcp dpt:80   from 0.0.0.0/0
ACCEPT tcp dpt:443  from 0.0.0.0/0
ACCEPT tcp dpt:9100 from 78.17.144.232
ACCEPT tcp dpt:8080 from 78.17.144.232
default DROP
```

`78.17.144.232` - IP `infra`, где работает Prometheus.

## 4. Docker и firewall

Docker создает собственные iptables chains. Поэтому одного `INPUT DROP` недостаточно для доказательства защиты контейнерных портов.

Проверять нужно:

```bash
sudo docker ps --format "table {{.Names}}\t{{.Ports}}"
sudo iptables -L DOCKER -n -v
sudo iptables -L DOCKER-USER -n -v
```

Если контейнер публикует порт наружу, это видно в `docker ps`, например:

```text
0.0.0.0:9100->9100/tcp
```

Для внутренних сервисов предпочтительно использовать `expose`, а не `ports`.

## 5. Nginx access control

Nginx является единственной публичной HTTP/HTTPS-точкой входа.

Административные UI закрываются Nginx Basic Auth:

- Prometheus;
- Alertmanager;
- MinIO Console;
- при необходимости Flower.

Grafana дополнительно имеет собственный login.

Vaultwarden не закрывается общей Basic Auth на весь сайт, потому что это ломает web-клиент, invite flow и мобильные клиенты. Защита Vaultwarden выполняется средствами самого Vaultwarden.

## 6. IP allowlist

Метрики:

```nginx
allow 78.17.144.232;
deny all;
```

Loki ingest:

```nginx
location /loki/api/v1/push {
    allow 130.49.129.180;
    allow 153.80.184.132;
    allow 78.17.144.232;
    allow 157.22.230.253;
    deny all;
    proxy_pass http://loki:3100/loki/api/v1/push;
}
```

Allowlist должен включать только серверы, где работает Grafana Alloy.

## 7. Vaultwarden

Vaultwarden хранит командные секреты и не должен быть открытым сервисом без ограничений.

Рекомендуемые настройки:

```env
SIGNUPS_ALLOWED=false
INVITATIONS_ALLOWED=true
ADMIN_TOKEN=<secret>
DOMAIN=https://vaultwarden.backuphub.spb.ru
```

Для rate limiting на уровне Nginx:

```nginx
limit_req_zone $binary_remote_addr zone=vaultwarden_login:10m rate=5r/m;

location /identity/accounts/prelogin {
    limit_req zone=vaultwarden_login burst=10 nodelay;
    proxy_pass http://vaultwarden:80;
}

location /identity/connect/token {
    limit_req zone=vaultwarden_login burst=10 nodelay;
    proxy_pass http://vaultwarden:80;
}
```

После onboarding команды свободная регистрация должна быть выключена.

## 8. TLS

TLS-сертификаты выпускаются через Certbot/Let's Encrypt.

Проверка сертификата:

```bash
openssl s_client -connect dev.backuphub.spb.ru:443 -servername dev.backuphub.spb.ru </dev/null 2>/dev/null | openssl x509 -noout -dates
```

Проверка certbot:

```bash
docker compose run --rm certbot renew --dry-run
```

Для новых доменов в существующий сертификат нужно перевыпустить сертификат со всем списком `-d`, а не только с новым доменом.

## 9. Secrets

Секреты не хранятся в git.

К секретам относятся:

- Django `SECRET_KEY`;
- PostgreSQL password;
- Redis password, если включен;
- Flower basic auth;
- MinIO root credentials;
- MinIO access keys для backup jobs;
- Telegram bot token;
- GitHub runner token;
- SSH private keys;
- Vaultwarden admin token;
- registry credentials.

Для `dev`, `prod`, `infra` и `secops` используются разные секреты.

Секреты должны храниться на сервере в env-файлах с ограниченными правами:

```bash
chmod 600 /opt/backuphub/app/.env
chown root:root /opt/backuphub/app/.env
```

## 10. Проверка публичной поверхности

На сервере:

```bash
sudo ss -tulpen
sudo docker ps --format "table {{.Names}}\t{{.Ports}}"
sudo ufw status verbose
sudo iptables -L ufw-user-input -n -v
```

С внешней машины:

```bash
nmap -Pn -p 80,443,8228,5432,6379,8000,8080,9100 <server_ip>
```

Ожидание: публично отвечают только `80`, `443`, `8228`; `8080/9100` доступны только с `infra`.

## 11. Правило обновления

PR, меняющий SSH, firewall, Nginx auth, allowlist, Vaultwarden, TLS, secrets или registry access, должен обновлять этот документ.
