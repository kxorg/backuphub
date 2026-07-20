# BackupHub

BackupHub — централизованная платформа для автоматизации, планирования и мониторинга резервного копирования целевых систем. Проект предоставляет REST API для управления конфигурациями бэкапов, оркеструет асинхронные задачи через распределённую очередь Celery/Redis и отслеживает статус выполнения операций в режиме реального времени.

---

## 📚 Навигация по документации

| Документ | Описание |
| :--- | :--- |
| 🚀 **[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)** | Руководство для разработчиков: запуск, тесты, структура кода |
| 🏗️ **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** | Архитектурные схемы и решения |
| 🌐 **[docs/INFRASTRUCTURE.md](docs/INFRASTRUCTURE.md)** | Инфраструктура и Docker-конфигурация |
| 🚢 **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** | CI/CD и деплой |
| 📊 **[docs/MONITORING.md](docs/MONITORING.md)** | Мониторинг и алерты |
| 🔒 **[docs/SECURITY.md](docs/SECURITY.md)** | Безопасность и авторизация |
| 💾 **[docs/BACKUPS.md](docs/BACKUPS.md)** | Управление резервными копиями |
| 🚨 **[docs/RUNBOOK.md](docs/RUNBOOK.md)** | Инструкции при инцидентах |
| 🤖 **[docs/github_runner.md](docs/github_runner.md)** | GitHub Actions Runners |
| 🔌 **[docs/BackupHub_API_Documentation.md](docs/API.md)** | Спецификация REST API |

---

## 🖥️ Инфраструктурные контуры

| Сервер | Назначение | Доступ |
| :--- | :--- | :--- |
| **dev.backuphub.spb.ru** | Тестовый стенд (Staging) | Внутренняя сеть (VPN) |
| **prod.backuphub.spb.ru** | Продакшн-контур | Изолированный сегмент |
| **infra.backuphub.spb.ru** | Мониторинг, логи, MinIO, Vault | Внутренняя сеть |
| **secops.backuphub.spb.ru** | CI/CD, реестр, SecOps | Изолированный сегмент |

![BackupHub infrastructure](docs/infrastructure-overview.png)

---

## 👥 Контакты ответственных

- **Выборнов Николай Юрьевич** — Team Lead 
- **Выборнов Дмитрий Юрьевич** — DevOps Engineer
- **Волков Александр Алексеевич** — DevOps Engineer
- **Булдаков Станислав Юрьевич** — Backend Developer
- **Ким Андрей Дмитриевич** — Backend Developer
- **Рубченко Максим Сергеевич** — Frontend Developer 💩

