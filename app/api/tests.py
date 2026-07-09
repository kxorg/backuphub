from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status

from core.models import (
    SystemType, Environment, BackupTool,
    TargetSystem, TargetSystemVersion,
    BackupConfiguration, BackupConfigurationVersion,
    BackupOperation,
)


class BackupOperationAPITestBase(TestCase):
    """Базовый класс с общими фикстурами."""

    def setUp(self):
        self.client = APIClient()

        # Справочники
        self.system_type = SystemType.objects.create(name='PostgreSQL')
        self.environment = Environment.objects.create(name='Production')
        self.backup_tool = BackupTool.objects.create(name='pg_dump')

        # Целевая система (с API-ключом)
        self.target_system = TargetSystem.objects.create(
            name='PG Main DB',
            system_type=self.system_type,
            environment=self.environment,
        )
        # Сохраняем API-ключ для передачи в заголовке
        self.api_key = str(self.target_system.api_key)

        # Версия системы (текущая)
        self.system_version = TargetSystemVersion.objects.create(
            target_system=self.target_system,
            version_number=1,
            owner='Ivanov',
            is_current=True,
            valid_from=timezone.now(),
        )

        # Конфигурация бэкапа
        self.config = BackupConfiguration.objects.create(
            name='Daily Backup',
            target_system_version=self.system_version,
            is_active=True,
        )

        # Версия конфигурации (текущая)
        self.config_version = BackupConfigurationVersion.objects.create(
            backup_configuration=self.config,
            backup_tool=self.backup_tool,
            version_number=1,
            backup_mode='full',
            is_current=True,
            valid_from=timezone.now(),
        )

        self.create_url = '/api/backup-operations/'

    def _create_payload(self, **overrides):
        """Базовый payload для создания операции (БЕЗ api_key — он в заголовке)."""
        payload = {
            'externalJobId': 'JOB-001',
            'hostname': 'backup-server-01',
            'ipAddress': '10.10.10.15',
            'startedAt': '2026-07-09T10:00:00Z',
        }
        payload.update(overrides)
        return payload


class RequiredAPITests(BackupOperationAPITestBase):
    """5 обязательных тестов из Definition of Done."""

    # ==========================================
    # ТЕСТ 1: Создание операции
    # ==========================================
    def test_1_create_operation(self):
        """Создание операции бэкапа с API-ключом в заголовке."""
        response = self.client.post(
            self.create_url,
            self._create_payload(),
            format='json',
            HTTP_X_API_KEY=self.api_key,  # ← API-ключ в заголовке
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)

        operation = BackupOperation.objects.get(id=response.data['id'])
        self.assertEqual(operation.status, 'in_progress')
        self.assertEqual(operation.hostname, 'backup-server-01')
        self.assertEqual(operation.external_job_id, 'JOB-001')
        self.assertEqual(
            operation.backup_configuration_version,
            self.config_version,
        )

    # ==========================================
    # ТЕСТ 2: Успешное завершение
    # ==========================================
    def test_2_successful_completion(self):
        """RUNNING → SUCCESS."""
        # Создаём операцию
        create_resp = self.client.post(
            self.create_url,
            self._create_payload(externalJobId='JOB-SUCCESS'),
            format='json',
            HTTP_X_API_KEY=self.api_key,
        )
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        op_id = create_resp.data['id']

        # Обновляем на SUCCESS
        response = self.client.patch(
            f'/api/backup-operations/{op_id}/',
            {
                'status': 'SUCCESS',
                'finishedAt': '2026-07-09T10:30:00Z',
                'sizeBytes': 5368709120,
                'storageType': 'S3',
                'storagePath': 's3://backup/prod/backup.sql.gz',
                'metadata': {'database': 'production_db', 'tables_count': 42},
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'SUCCESS')

        operation = BackupOperation.objects.get(id=op_id)
        self.assertEqual(operation.status, 'success')
        self.assertEqual(operation.size_bytes, 5368709120)

    # ==========================================
    # ТЕСТ 3: Завершение с ошибкой
    # ==========================================
    def test_3_completion_with_error(self):
        """RUNNING → FAILED."""
        create_resp = self.client.post(
            self.create_url,
            self._create_payload(externalJobId='JOB-FAILED'),
            format='json',
            HTTP_X_API_KEY=self.api_key,
        )
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        op_id = create_resp.data['id']

        response = self.client.patch(
            f'/api/backup-operations/{op_id}/',
            {
                'status': 'FAILED',
                'finishedAt': '2026-07-09T10:15:00Z',
                'errorMessage': 'Connection timeout to S3 storage',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'FAILED')

        operation = BackupOperation.objects.get(id=op_id)
        self.assertEqual(operation.status, 'error')
        self.assertEqual(operation.error_message, 'Connection timeout to S3 storage')

    # ==========================================
    # ТЕСТ 4: Попытка повторного завершения
    # ==========================================
    def test_4_attempt_to_complete_again(self):
        """Запрет изменения завершённой операции."""
        create_resp = self.client.post(
            self.create_url,
            self._create_payload(externalJobId='JOB-RETRY'),
            format='json',
            HTTP_X_API_KEY=self.api_key,
        )
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        op_id = create_resp.data['id']
        url = f'/api/backup-operations/{op_id}/'

        # Завершаем успешно
        self.client.patch(
            url,
            {'status': 'SUCCESS', 'finishedAt': '2026-07-09T10:30:00Z'},
            format='json',
        )

        # Пытаемся изменить снова
        response = self.client.patch(
            url,
            {'status': 'FAILED', 'errorMessage': 'Late error'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        operation = BackupOperation.objects.get(id=op_id)
        self.assertEqual(operation.status, 'success')

    # ==========================================
    # ТЕСТ 5: Несуществующая конфигурация
    # ==========================================
    def test_5_nonexistent_configuration(self):
        """Создание операции с несуществующим configurationId."""
        response = self.client.post(
            self.create_url,
            self._create_payload(configurationId=9999),
            format='json',
            HTTP_X_API_KEY=self.api_key,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)