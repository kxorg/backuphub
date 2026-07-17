# BackupHub

BackupHub — централизованная платформа для автоматизации, планирования и мониторинга резервного копирования целевых систем. Проект предоставляет REST API для управления конфигурациями бэкапов, оркеструет асинхронные задачи через распределенную очередь Celery/Redis и отслеживает статус выполнения операций в режиме реального времени.

---

## 🗺️ Архитектура системы

Логическая схема взаимодействия сервисов, сетевых потоков и слоев хранения данных:

---

## 📚 Навигация по документации

| Документ | Целевая аудитория и назначение |
| :--- | :--- |
| 🚀 **[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)** | **Разработчикам:** Полная структура проекта, развертывание dev-окружения, миграции, сигналы, API эндпоинты, тесты. |
| 🏗️ **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** | **Архитекторам:** Схемы данных, граф зависимостей сервисов и логика изоляции слоев. |
| 🌐 **[docs/INFRASTRUCTURE.md](docs/INFRASTRUCTURE.md)** | **DevOps:** Сетевая топология, конфигурация Docker-сетей, тома хранения и лимиты ресурсов. |
| 🚢 **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** | **DevOps:** CI/CD пайплайны, сборка production-образов, деплой на целевые сервера. |
| 📊 **[docs/MONITORING.md](docs/MONITORING.md)** | **SRE / С运维:** Сбор метрик Celery/Django, алертинг, интеграция с Telegram. |
| 🔒 **[docs/SECURITY.md](docs/SECURITY.md)** | **SecOps:** Механизм кастомной авторизации, шифрование учетных записей целевых систем. |
| 💾 **[docs/BACKUPS.md](docs/BACKUPS.md)** | **Администраторам:** Ротация архивов, проверка целостности и методы сжатия бэкапов. |
| 🚨 **[docs/RUNBOOK.md](docs/RUNBOOK.md)** | **Дежурным инженерам:** Реакция на инциденты (отказ базы, падение воркеров, переполнение диска). |
| 🤖 **[docs/github_runner.md](docs/github_runner.md)** | **DevOps:** Инструкция по сопровождению изолированных GitHub Actions Runners. |
| 🔌 **[docs/BackupHub_API_Documentation.md](docs/BackupHub_API_Documentation.md)** | **Интеграторам:** Спецификация REST API v1, схемы JSON-валидации и коды ответов. |

---

## 🖥️ Инфраструктурные контуры

| Доменное имя | Назначение сервера | Доступность |
| :--- | :--- | :--- |
| **dev.backuphub.spb.ru** | Стенд для интеграционного тестирования и проверки веток (Staging). | Внутренняя сеть (VPN) |
| **prod.backuphub.spb.ru** | Продакшн-контур исполнения боевых задач бэкапа. | Изолированный сегмент |
| **infra.backuphub.spb.ru** | Мониторинг, логирование (Grafana), Redis-брокеры. | Внутренняя сеть |
| **secops.backuphub.spb.ru** | Управление секретами (Vault), аудит ключей доступа. | Изолированный сегмент |

---

## Celery
Celery используется как надежная распределенная система для обработки асинхронных задач резервного копирования. Обеспечивает отказоустойчивость при подключении к удаленным серверам и выполнении тяжелых I/O операций.

## Celery Beat
Используется для запуска бэкапов по заданному расписанию (CRON).
В BackupHub расписания динамически синхронизируются с базой данных через сигналы Django. Добавление или удаление BackupConfiguration автоматически обновляет расписание в Celery Beat без необходимости перезапуска сервисов.

## Flower
Предоставляет дашборд реального времени для отслеживания состояния воркеров, истории выполнения задач бэкапа и потребления ресурсов.

## Prometheus & Grafana
Prometheus: Сбор метрик производительности системы (Celery, Nginx, Django).
Grafana: Визуализация аналитики, дашборды для мониторинга успешных/упавших задач бэкапа.

## Testing section
Ручное тестирование в локальном Docker-окружении:

## CI:
- Проверка линтерами (Lint).
- Интеграционные тесты (Pytest).
- Запуск тестов внутри контейнера: 

```shell
docker exec -it bh_app_local pytest -v
```

## Local development
Убедитесь, что установлен Docker engine.

```shell
git clone git@github.com:kim-andrey/backuphub.git
cd backuphub && docker-compose -f docker-compose.local.yml up -d
```

- http://0.0.0.0:8000/api/v1/ - Точка доступа REST API.
- http://0.0.0.0:8000/admin/ - Панель администратора Django. (Создание суперпользователя: python manage.py createsuperuser).
- http://0.0.0.0:5555/flower - Flower для отслеживания Celery задач.
- http://0.0.0.0:3000/ - Grafana дашборды

## Endpoints v1 (X-API-KEY Auth)
- Target Systems
- GET /api/v1/targets/ - Получить список целевых систем.
- POST /api/v1/targets/ - Зарегистрировать новую систему.

## Backup Configurations
- GET /api/v1/configurations/ - Список настроенных правил расписания бэкапов.
- POST /api/v1/configurations/ - Создать новое расписание.
- PATCH /api/v1/configurations/{id}/ - Частичное обновление (например, отключение активности расписания).

## Operations
- GET /api/v1/operations/ - История и статусы запусков резервного копирования.

## Infrastructure and CI/CD
- Основано на CentOS / Ubuntu (в зависимости от целевого хоста).

## Server configuration
```shell
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl start docker
mkdir -p /opt/deploy/backuphub
cd /opt/deploy/backuphub
```

## Generate SSH key for GitHub
```shell
ssh-keygen -t rsa -b 4096 -C "deploy@backuphub.local" -f ~/.ssh/deploy_key
cat ~/.ssh/deploy_key.pub
```

