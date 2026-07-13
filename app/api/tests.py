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
    """Тесты для Backup Operations API (snake_case + auto version)."""

    def setUp(self):
        self.client = APIClient()

        self.system_type = SystemType.objects.create(name='PostgreSQL')
        self.environment = Environment.objects.create(name='Production')
        self.backup_tool = BackupTool.objects.create(name='pg_dump')

        self.target_system = TargetSystem.objects.create(
            name='PG Main DB',
            system_type=self.system_type,
            environment=self.environment,
        )
        self.api_key = str(self.target_system.api_key)

        self.system_version = TargetSystemVersion.objects.create(
            target_system=self.target_system,
            version_number=1,
            owner='Ivanov',
            is_current=True,
            valid_from=timezone.now(),
        )

        self.config = BackupConfiguration.objects.create(
            name='Daily Backup',
            target_system_version=self.system_version,
            is_active=True,
        )

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
        """Базовый payload для создания операции (только snake_case)."""
        data = {
            'backup_configuration_id': self.config.id,
            'hostname': 'backup-server-01',
            'ip_address': '10.10.10.15',
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
        # Привязка к ТЕКУЩЕЙ версии конфигурации (бэкенд нашел её сам)
        self.assertEqual(op.backup_configuration_version, self.config_version)
        self.assertIsNotNone(op.started_at)

    # ==========================================
    # 2. Успешное завершение (RUNNING → SUCCESS)
    # ==========================================
    def test_successful_completion(self):
        """PATCH на SUCCESS → 200 OK, finished_at ставится автоматически."""
        op_id = self._create_op()

        resp = self.client.patch(
            f'{self.url}{op_id}/',
            {
                'status': 'SUCCESS',
                'size_bytes': 5368709120,
                'storage_type': 's3',
                'storage_path': 's3://backup/prod/backup.sql.gz',
            },
            format='json',
            HTTP_X_API_KEY=self.api_key,
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['status'], 'SUCCESS')

        op = BackupOperation.objects.get(id=op_id)
        self.assertEqual(op.status, 'success')
        self.assertEqual(op.size_bytes, 5368709120)
        self.assertIsNotNone(op.finished_at)

    # ==========================================
    # 3. Завершение с ошибкой (RUNNING → FAILED)
    # ==========================================
    def test_completion_with_error(self):
        """PATCH на FAILED → 200 OK."""
        op_id = self._create_op()

        resp = self.client.patch(
            f'{self.url}{op_id}/',
            {
                'status': 'FAILED',
                'error_message': 'Connection timeout to S3',
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

        self.client.patch(
            url,
            {'status': 'SUCCESS'},
            format='json',
            HTTP_X_API_KEY=self.api_key,
        )

        resp = self.client.patch(
            url,
            {'status': 'FAILED', 'error_message': 'Late error'},
            format='json',
            HTTP_X_API_KEY=self.api_key,
        )

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

        op = BackupOperation.objects.get(id=op_id)
        self.assertEqual(op.status, 'success')

    # ==========================================
    # 5. Несуществующая конфигурация
    # ==========================================
    def test_nonexistent_configuration(self):
        """POST с несуществующим backup_configuration_id → 400 Bad Request."""
        resp = self.client.post(
            self.url,
            {'backup_configuration_id': 9999},
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
        )

        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)