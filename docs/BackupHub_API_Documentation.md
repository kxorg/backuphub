# 📚 BackupHub API Documentation

## 📋 Содержание

1. [Обзор](#обзор)
2. [Аутентификация](#аутентификация)
3. [Эндпоинты](#эндпоинты)
   - [Создание операции](#1-создание-операции-бэкапа)
   - [Обновление операции](#2-обновление-операции-бэкапа)
   - [Список операций](#3-получение-списка-операций)
   - [Детали операции](#4-получение-деталей-операции)
4. [Маппинг статусов](#маппинг-статусов)
5. [Обработка ошибок](#обработка-ошибок)
6. [Примеры использования](#примеры-использования)
7. [Тестирование](#тестирование)

---

## 🔍 Обзор

API предоставляет интерфейс для управления операциями резервного копирования. Используется внешними скриптами и агентами бэкапа для:

- Регистрации начала выполнения задачи
- Обновления статуса и метаданных после завершения
- Получения истории операций

**Base URL:**
```
http://<your-domain>/api/backup-operations/
```

---

## 🔐 Аутентификация

Все запросы к API (POST, PATCH) требуют аутентификации через заголовок `X-API-Key`.

### Заголовок

| Заголовок | Значение | Обязательный |
|-----------|----------|--------------|
| `X-API-Key` | UUID ключа целевой системы (`TargetSystem.api_key`) | ✅ Да |

### Где взять API-ключ

1. Откройте админ-панель Django: `http://<your-domain>/admin/`
2. Перейдите в раздел **Target Systems**
3. Выберите нужную систему
4. Скопируйте значение поля **API Key**

### Принцип работы

- API-ключ привязан к конкретной системе (`TargetSystem`)
- При создании операции система определяется автоматически по ключу
- При обновлении операции проверяется, что ключ соответствует системе, которой принадлежит операция
- Неверный или отсутствующий ключ возвращает `401 Unauthorized`

---

## 🌐 Эндпоинты

### 1. Создание операции бэкапа

Регистрирует начало выполнения задачи бэкапа. Система автоматически находит текущую активную версию конфигурации.

**Endpoint:**
```
POST /api/backup-operations/
```

**Headers:**
```http
Content-Type: application/json
X-API-Key: <your-system-api-key>
```

**Request Body:**

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| `externalJobId` | string | ✅ | Уникальный ID задачи во внешней системе (cron, Jenkins, K8s) |
| `hostname` | string | ✅ | Имя хоста, где выполняется бэкап |
| `ipAddress` | string | ❌ | IP-адрес хоста. Если не указан, определяется автоматически |
| `startedAt` | datetime | ✅ | Время начала выполнения (ISO 8601) |
| `configurationId` | integer | ❌ | ID конфигурации. Если не указан, используется первая активная конфигурация системы |

**Пример запроса:**
```json
{
  "externalJobId": "JOB-2026-07-10-001",
  "hostname": "db-prod-01",
  "ipAddress": "192.168.1.10",
  "startedAt": "2026-07-10T10:00:00Z"
}
```

**Response (201 Created):**
```json
{
  "id": 105
}
```

**Логика работы:**
1. Получает `TargetSystem` из заголовка `X-API-Key`
2. Находит текущую версию системы (`is_current=True`)
3. Находит активную конфигурацию для этой системы
4. Находит текущую версию конфигурации (`is_current=True`)
5. Создаёт операцию с привязкой к текущей версии конфигурации
6. Проверяет уникальность `externalJobId`

---

### 2. Обновление операции бэкапа

Обновляет статус и метаданные операции после завершения.

**Endpoint:**
```
PATCH /api/backup-operations/{id}/
```

**Headers:**
```http
Content-Type: application/json
X-API-Key: <your-system-api-key>
```

**Request Body:**

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| `status` | string | ✅ | `SUCCESS` или `FAILED` |
| `finishedAt` | datetime | ❌ | Время завершения (ISO 8601) |
| `sizeBytes` | integer | ❌ | Размер бэкапа в байтах |
| `storageType` | string | ❌ | Тип хранилища (`S3`, `local`, `NFS`, `azure`, `gcs`) |
| `storagePath` | string | ❌ | Путь к файлу бэкапа |
| `metadata` | object | ❌ | Дополнительные технические данные (JSON) |
| `errorMessage` | string | ⚠️ | **Обязательно**, если `status: FAILED` |

**Пример запроса (успех):**
```json
{
  "status": "SUCCESS",
  "finishedAt": "2026-07-10T10:45:00Z",
  "sizeBytes": 5368709120,
  "storageType": "S3",
  "storagePath": "s3://backups/prod/db-01/backup.sql.gz",
  "metadata": {
    "database": "production",
    "tables_count": 42,
    "compression": "gzip"
  }
}
```

**Пример запроса (ошибка):**
```json
{
  "status": "FAILED",
  "finishedAt": "2026-07-10T10:05:00Z",
  "errorMessage": "Connection timeout to S3 storage"
}
```

**Response (200 OK):**
```json
{
  "id": 105,
  "backupConfigurationId": 5,
  "externalJobId": "JOB-2026-07-10-001",
  "hostname": "db-prod-01",
  "ipAddress": "192.168.1.10",
  "status": "SUCCESS",
  "startedAt": "2026-07-10T10:00:00Z",
  "finishedAt": "2026-07-10T10:45:00Z",
  "sizeBytes": 5368709120,
  "storageType": "S3",
  "storagePath": "s3://backups/prod/db-01/backup.sql.gz",
  "metadata": {
    "database": "production",
    "tables_count": 42,
    "compression": "gzip"
  },
  "errorMessage": null
}
```

**Ограничения:**
- Разрешённые переходы: `RUNNING` → `SUCCESS`, `RUNNING` → `FAILED`
- Запрещённые переходы: `SUCCESS` → `FAILED`, `FAILED` → `SUCCESS`
- Завершённые операции нельзя изменять повторно
- API-ключ должен соответствовать системе, которой принадлежит операция

---

### 3. Получение списка операций

Возвращает историю выполненных операций с поддержкой фильтрации.

**Endpoint:**
```
GET /api/backup-operations/
```

**Query Parameters:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `status` | string | Фильтр по статусу: `RUNNING`, `SUCCESS`, `FAILED` |
| `backupConfigurationId` | integer | Фильтр по ID конфигурации |

**Пример запроса:**
```http
GET /api/backup-operations/?status=SUCCESS&backupConfigurationId=5
```

**Response (200 OK):**
```json
[
  {
    "id": 105,
    "backupConfigurationId": 5,
    "externalJobId": "JOB-2026-07-10-001",
    "hostname": "db-prod-01",
    "ipAddress": "192.168.1.10",
    "status": "SUCCESS",
    "startedAt": "2026-07-10T10:00:00Z",
    "finishedAt": "2026-07-10T10:45:00Z",
    "sizeBytes": 5368709120,
    "storageType": "S3",
    "storagePath": "s3://backups/prod/db-01/backup.sql.gz",
    "metadata": { ... },
    "errorMessage": null
  },
  {
    "id": 106,
    "backupConfigurationId": 5,
    "externalJobId": "JOB-2026-07-10-002",
    "hostname": "db-prod-02",
    "status": "FAILED",
    ...
  }
]
```

---

### 4. Получение деталей операции

Возвращает полную информацию об одной конкретной операции.

**Endpoint:**
```
GET /api/backup-operations/{id}/
```

**Response (200 OK):**
```json
{
  "id": 105,
  "backupConfigurationId": 5,
  "externalJobId": "JOB-2026-07-10-001",
  "hostname": "db-prod-01",
  "ipAddress": "192.168.1.10",
  "status": "SUCCESS",
  "startedAt": "2026-07-10T10:00:00Z",
  "finishedAt": "2026-07-10T10:45:00Z",
  "sizeBytes": 5368709120,
  "storageType": "S3",
  "storagePath": "s3://backups/prod/db-01/backup.sql.gz",
  "metadata": {
    "database": "production",
    "tables_count": 42,
    "compression": "gzip"
  },
  "errorMessage": null
}
```

**Response (404 Not Found):**
```json
{
  "detail": "Not found."
}
```

---

## 🔄 Маппинг статусов

API использует следующие статусы, которые внутри системы маппятся следующим образом:

| API Status | DB Status | Описание |
|------------|-----------|----------|
| `RUNNING` | `in_progress` | Бэкап выполняется |
| `SUCCESS` | `success` | Бэкап успешно завершён |
| `FAILED` | `error` | Бэкап завершился с ошибкой |

При создании операции статус автоматически устанавливается в `RUNNING` (`in_progress`).

---

## 🛡️ Обработка ошибок

| Код | Описание | Причина |
|-----|----------|---------|
| `200 OK` | Успех | Запрос выполнен успешно |
| `201 Created` | Создано | Операция успешно создана |
| `400 Bad Request` | Ошибка валидации | Неверный формат данных, дубликат `externalJobId`, отсутствие обязательных полей, попытка изменить завершённую операцию |
| `401 Unauthorized` | Не авторизован | Неверный API-ключ, отсутствует заголовок `X-API-Key` |
| `403 Forbidden` | Доступ запрещён | Попытка обновить операцию, принадлежащую другой системе |
| `404 Not Found` | Не найдено | Операция с указанным ID не существует |

### Примеры ошибок

**400 Bad Request — дубликат externalJobId:**
```json
{
  "externalJobId": ["Operation with externalJobId='JOB-001' already exists."]
}
```

**400 Bad Request — несуществующая конфигурация:**
```json
{
  "configurationId": ["Configuration with id=9999 not found for this system."]
}
```

**400 Bad Request — повторное завершение:**
```json
{
  "non_field_errors": ["Cannot modify completed operation."]
}
```

**400 Bad Request — FAILED без errorMessage:**
```json
{
  "errorMessage": ["This field is required for FAILED status."]
}
```

**401 Unauthorized — неверный API-ключ:**
```json
{
  "detail": "Invalid API key."
}
```

**403 Forbidden — чужой API-ключ:**
```json
{
  "error": "API key does not match the operation's target system."
}
```

---

## 💻 Примеры использования

### cURL

#### 1. Начать бэкап
```bash
curl -X POST http://localhost:8000/api/backup-operations/ \
  -H "Content-Type: application/json" \
  -H "X-API-Key: 54d2e7b7-c231-4cfa-aabb-0ed9996614f7" \
  -d '{
    "externalJobId": "cron-daily-001",
    "hostname": "web-server-01",
    "startedAt": "2026-07-10T02:00:00Z"
  }'
```

#### 2. Завершить бэкап успешно
```bash
curl -X PATCH http://localhost:8000/api/backup-operations/105/ \
  -H "Content-Type: application/json" \
  -H "X-API-Key: 54d2e7b7-c231-4cfa-aabb-0ed9996614f7" \
  -d '{
    "status": "SUCCESS",
    "finishedAt": "2026-07-10T02:30:00Z",
    "sizeBytes": 1073741824,
    "storagePath": "/mnt/backups/web-01.tar.gz"
  }'
```

#### 3. Завершить бэкап с ошибкой
```bash
curl -X PATCH http://localhost:8000/api/backup-operations/106/ \
  -H "Content-Type: application/json" \
  -H "X-API-Key: 54d2e7b7-c231-4cfa-aabb-0ed9996614f7" \
  -d '{
    "status": "FAILED",
    "errorMessage": "Disk full"
  }'
```

#### 4. Получить список операций
```bash
curl -X GET "http://localhost:8000/api/backup-operations/?status=SUCCESS"
```

#### 5. Получить детали операции
```bash
curl -X GET http://localhost:8000/api/backup-operations/105/
```

### Python (requests)

```python
import requests

API_URL = "http://localhost:8000/api/backup-operations/"
API_KEY = "54d2e7b7-c231-4cfa-aabb-0ed9996614f7"
HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY
}

# 1. Создать операцию
response = requests.post(API_URL, headers=HEADERS, json={
    "externalJobId": "JOB-001",
    "hostname": "db-server-01",
    "startedAt": "2026-07-10T10:00:00Z"
})
operation_id = response.json()["id"]

# 2. Обновить статус
response = requests.patch(
    f"{API_URL}{operation_id}/",
    headers=HEADERS,
    json={
        "status": "SUCCESS",
        "finishedAt": "2026-07-10T10:30:00Z",
        "sizeBytes": 5368709120
    }
)

# 3. Получить список
response = requests.get(f"{API_URL}?status=SUCCESS")
operations = response.json()
```

---

## 🧪 Тестирование

### Запуск тестов

```bash
# Все тесты API
python manage.py test api -v 2

# Конкретный тест
python manage.py test api.tests.BackupOperationAPITests.test_create_operation -v 2
```

### Список тестов

| # | Тест | Описание |
|---|------|----------|
| 1 | `test_create_operation` | Создание операции с валидным API-ключом |
| 2 | `test_successful_completion` | Успешное завершение (RUNNING → SUCCESS) |
| 3 | `test_completion_with_error` | Завершение с ошибкой (RUNNING → FAILED) |
| 4 | `test_attempt_to_complete_again` | Попытка повторного завершения (400) |
| 5 | `test_nonexistent_configuration` | Несуществующая конфигурация (400) |
| 6 | `test_post_without_api_key` | POST без API-ключа (401) |
| 7 | `test_patch_without_api_key` | PATCH без API-ключа (401) |

### Ожидаемый результат

```
test_attempt_to_complete_again ... ok
test_completion_with_error ... ok
test_create_operation ... ok
test_nonexistent_configuration ... ok
test_patch_without_api_key ... ok
test_post_without_api_key ... ok
test_successful_completion ... ok

----------------------------------------------------------------------
Ran 7 tests in 1.5s

OK
```

---

## 📖 Swagger UI

Интерактивная документация доступна по адресу:

👉 **http://localhost:8000/api/docs/**

Там вы можете тестировать эндпоинты прямо в браузере.

---

## 🔗 Структура проекта

```
api/
├── __init__.py
├── apps.py
├── authentication.py    # Кастомная аутентификация через X-API-Key
├── serializers.py       # Сериализаторы для API
├── tests.py            # API тесты
├── urls.py             # Маршруты API
└── views.py            # ViewSet для BackupOperation
```

---

## 📝 Changelog

### v1.0.0 (2026-07-10)

- ✅ Реализован POST создания операции
- ✅ Реализован PATCH обновления статуса
- ✅ Реализован GET списка операций с фильтрами
- ✅ Реализован GET деталей операции
- ✅ Аутентификация через заголовок X-API-Key
- ✅ Проверка соответствия API-ключа системе операции
- ✅ Маппинг статусов API ↔ DB
- ✅ Валидация переходов статусов
- ✅ Проверка уникальности externalJobId
- ✅ Автоматическая привязка к текущей версии конфигурации
- ✅ 7 API тестов
- ✅ Swagger документация

---

## 📞 Поддержка

По вопросам работы API обращайтесь:
- Email: support@backuphub.local
- Swagger: http://localhost:8000/api/docs/

---

**© 2026 BackupHub. All rights reserved.**
```

Готово! Просто скопируй этот текст и сохрани в файл `api.md` или `README.md`. 📄✨