from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from core.models import (
    SystemType, Environment, BackupTool,
    TargetSystem, TargetSystemVersion,
    BackupConfiguration, BackupConfigurationVersion,
    BackupOperation,
)


class BackupOperationAPITests(TestCase):
    """Тесты для Backup Operations API (обновлённый контракт)."""

    def setUp(self):
        self.client = APIClient()

        # Справочники
        self.system_type = SystemType.objects.create(name='PostgreSQL')
        self.environment = Environment.objects.create(name='Production')
        self.backup_tool = BackupTool.objects.create(name='pg_dump')

        # Целевая система с API-ключом
        self.target_system = TargetSystem.objects.create(
            name='PG Main DB',
            system_type=self.system_type,
            environment=self.environment,
        )
        self.api_key = str(self.target_system.api_key)

        # Текущая версия системы
        self.system_version = TargetSystemVersion.objects.create(
            target_system=self.target_system,
            version_number=1,
            owner='Ivanov',
            is_current=True,
            valid_from=timezone.now(),
        )

        # Конфигурация
        self.config = BackupConfiguration.objects.create(
            name='Daily Backup',
            target_system_version=self.system_version,
            is_active=True,
        )

        # Текущая версия конфигурации
        self.config_version = BackupConfigurationVersion.objects.create(
            backup_configuration=self.config,
            backup_tool=self.backup_tool,
            version_number=1,
            backup_mode='full',
            is_current=True,
            valid_from=timezone.now(),
        )

        self.url = '/api/backup-operations/'

    def _payload(self, **overrides):
        """Базовый payload для создания операции."""
        data = {
            'backupConfigurationVersionId': self.config_version.id,
            'hostname': 'backup-server-01',
            'ipAddress': '10.10.10.15',
        }
        data.update(overrides)
        return data

    def _create_op(self, **overrides):
        """Хелпер: создаёт операцию и возвращает её ID."""
        resp = self.client.post(
            self.url,
            self._payload(**overrides),
            format='json',
            HTTP_X_API_KEY=self.api_key,
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        return resp.data['id']

    # ==========================================
    # 1. Создание операции (POST с ключом)
    # ==========================================
    def test_create_operation(self):
        """POST с валидным API-ключом → 201 Created."""
        resp = self.client.post(
            self.url,
            self._payload(),
            format='json',
            HTTP_X_API_KEY=self.api_key,
        )

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', resp.data)

        op = BackupOperation.objects.get(id=resp.data['id'])
        self.assertEqual(op.status, 'in_progress')
        self.assertEqual(op.hostname, 'backup-server-01')
        # Привязка к переданной версии конфигурации
        self.assertEqual(op.backup_configuration_version, self.config_version)
        # started_at должен быть установлен автоматически
        self.assertIsNotNone(op.started_at)

    # ==========================================
    # 2. Успешное завершение (RUNNING → SUCCESS)
    # ==========================================
    def test_successful_completion(self):
        """PATCH на SUCCESS → 200 OK, finished_at ставится автоматически."""
        op_id = self._create_op()

        # finishedAt больше не передаётся в body
        resp = self.client.patch(
            f'{self.url}{op_id}/',
            {
                'status': 'SUCCESS',
                'sizeBytes': 5368709120,
                'storageType': 's3',
                'storagePath': 's3://backup/prod/backup.sql.gz',
            },
            format='json',
            HTTP_X_API_KEY=self.api_key,
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['status'], 'SUCCESS')

        op = BackupOperation.objects.get(id=op_id)
        self.assertEqual(op.status, 'success')
        self.assertEqual(op.size_bytes, 5368709120)
        # Проверка, что finished_at установился автоматически
        self.assertIsNotNone(op.finished_at)

    # ==========================================
    # 3. Завершение с ошибкой (RUNNING → FAILED)
    # ==========================================
    def test_completion_with_error(self):
        """PATCH на FAILED → 200 OK, finished_at ставится автоматически."""
        op_id = self._create_op()

        resp = self.client.patch(
            f'{self.url}{op_id}/',
            {
                'status': 'FAILED',
                'errorMessage': 'Connection timeout to S3',
            },
            format='json',
            HTTP_X_API_KEY=self.api_key,
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['status'], 'FAILED')

        op = BackupOperation.objects.get(id=op_id)
        self.assertEqual(op.status, 'error')
        self.assertEqual(op.error_message, 'Connection timeout to S3')
        self.assertIsNotNone(op.finished_at)

    # ==========================================
    # 4. Попытка повторного завершения
    # ==========================================
    def test_attempt_to_complete_again(self):
        """PATCH завершённой операции → 400 Bad Request."""
        op_id = self._create_op()
        url = f'{self.url}{op_id}/'

        # Сначала завершаем успешно
        self.client.patch(
            url,
            {'status': 'SUCCESS'},
            format='json',
            HTTP_X_API_KEY=self.api_key,
        )

        # Пытаемся изменить снова
        resp = self.client.patch(
            url,
            {'status': 'FAILED', 'errorMessage': 'Late error'},
            format='json',
            HTTP_X_API_KEY=self.api_key,
        )

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

        # Статус в БД не изменился
        op = BackupOperation.objects.get(id=op_id)
        self.assertEqual(op.status, 'success')

    # ==========================================
    # 5. Несуществующая версия конфигурации
    # ==========================================
    def test_nonexistent_configuration_version(self):
        """POST с несуществующим backupConfigurationVersionId → 400 Bad Request."""
        resp = self.client.post(
            self.url,
            {'backupConfigurationVersionId': 9999},
            format='json',
            HTTP_X_API_KEY=self.api_key,
        )

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # ==========================================
    # 6. POST без API-ключа
    # ==========================================
    def test_post_without_api_key(self):
        """POST без заголовка X-API-Key → 401 Unauthorized."""
        resp = self.client.post(
            self.url,
            self._payload(),
            format='json',
            # Нет HTTP_X_API_KEY
        )

        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    # ==========================================
    # 7. PATCH без API-ключа
    # ==========================================
    def test_patch_without_api_key(self):
        """PATCH без заголовка X-API-Key → 401 Unauthorized."""
        op_id = self._create_op()

        resp = self.client.patch(
            f'{self.url}{op_id}/',
            {'status': 'SUCCESS'},
            format='json',
            # Нет HTTP_X_API_KEY
        )

        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)