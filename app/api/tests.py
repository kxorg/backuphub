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
    """Базовый класс с общими фикстурами для всех тестов."""

    def setUp(self):
        """Создаёт тестовые данные перед каждым тестом."""
        self.client = APIClient()
        
        # Создаём тестового пользователя для авторизации
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

        # Справочники
        self.system_type = SystemType.objects.create(
            name='PostgreSQL',
            description='PostgreSQL database'
        )
        self.environment = Environment.objects.create(
            name='Production',
            description='Production environment'
        )
        self.backup_tool = BackupTool.objects.create(
            name='pg_dump',
            description='PostgreSQL logical backup'
        )

        # Целевая система
        self.target_system = TargetSystem.objects.create(
            name='PG Main DB',
            system_type=self.system_type,
            environment=self.environment,
            description='Main production database'
        )

        # Версия системы (текущая)
        self.system_version = TargetSystemVersion.objects.create(
            target_system=self.target_system,
            version_number=1,
            owner='Ivanov I.I.',
            administrator='Petrov P.P.',
            is_current=True,
            valid_from=timezone.now()
        )

        # Конфигурация бэкапа
        self.config = BackupConfiguration.objects.create(
            name='Daily PostgreSQL Backup',
            target_system_version=self.system_version,
            description='Daily logical backup',
            is_active=True
        )

        # Версия конфигурации (текущая)
        self.config_version = BackupConfigurationVersion.objects.create(
            backup_configuration=self.config,
            backup_tool=self.backup_tool,
            version_number=1,
            backup_mode='full',
            schedule_cron='0 2 * * *',
            retention_days=30,
            rpo_minutes=1440,
            rto_minutes=60,
            storage_type='s3',
            storage_path='s3://backups/prod/',
            is_current=True,
            valid_from=timezone.now()
        )

        # URL для создания операции
        self.create_url = '/api/backup-operations/'

    def _create_payload(self, **overrides):
        """Базовый payload для создания операции."""
        payload = {
            'backupConfigurationId': self.config.id,
            'externalJobId': 'JOB-001',
            'hostname': 'backup-server-01',
            'ipAddress': '10.10.10.15',
            'startedAt': '2026-07-09T10:00:00Z'
        }
        payload.update(overrides)
        return payload


# ==========================================
# 5 ОБЯЗАТЕЛЬНЫХ ТЕСТОВ ИЗ DEFINITION OF DONE
# ==========================================

class RequiredAPITests(BackupOperationAPITestBase):
    """5 обязательных тестов из Definition of Done."""

    def test_1_create_operation(self):
        """Тест 1: Создание операции."""
        response = self.client.post(
            self.create_url,
            self._create_payload(),
            format='json'
        )
        
        # Проверяем статус ответа
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Проверяем, что в ответе есть ID
        self.assertIn('id', response.data)
        operation_id = response.data['id']
        
        # Проверяем, что операция создана в БД
        operation = BackupOperation.objects.get(id=operation_id)
        self.assertEqual(operation.status, 'in_progress')
        self.assertEqual(operation.hostname, 'backup-server-01')
        self.assertEqual(operation.external_job_id, 'JOB-001')
        
        # Проверяем, что операция привязана к ТЕКУЩЕЙ версии конфигурации
        self.assertEqual(operation.backup_configuration_version, self.config_version)

    def test_2_successful_completion(self):
        """Тест 2: Успешное завершение."""
        # Сначала создаём операцию
        create_response = self.client.post(
            self.create_url,
            self._create_payload(externalJobId='JOB-SUCCESS'),
            format='json'
        )
        operation_id = create_response.data['id']
        update_url = f'/api/backup-operations/{operation_id}/'
        
        # Обновляем на SUCCESS
        response = self.client.patch(
            update_url,
            {
                'status': 'SUCCESS',
                'finishedAt': '2026-07-09T10:30:00Z',
                'sizeBytes': 5368709120,
                'storageType': 'S3',
                'storagePath': 's3://backup/prod/backup.sql.gz',
                'metadata': {'database': 'production_db', 'tables_count': 42}
            },
            format='json'
        )
        
        # Проверяем статус ответа
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Проверяем, что статус обновился в БД
        operation = BackupOperation.objects.get(id=operation_id)
        self.assertEqual(operation.status, 'success')
        self.assertEqual(operation.size_bytes, 5368709120)
        self.assertEqual(operation.storage_type, 'S3')
        
        # Проверяем, что статус в ответе API — SUCCESS
        self.assertEqual(response.data['status'], 'SUCCESS')

    def test_3_completion_with_error(self):
        """Тест 3: Завершение с ошибкой."""
        # Сначала создаём операцию
        create_response = self.client.post(
            self.create_url,
            self._create_payload(externalJobId='JOB-FAILED'),
            format='json'
        )
        operation_id = create_response.data['id']
        update_url = f'/api/backup-operations/{operation_id}/'
        
        # Обновляем на FAILED
        response = self.client.patch(
            update_url,
            {
                'status': 'FAILED',
                'finishedAt': '2026-07-09T10:15:00Z',
                'errorMessage': 'Connection timeout to S3 storage'
            },
            format='json'
        )
        
        # Проверяем статус ответа
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Проверяем, что статус обновился в БД
        operation = BackupOperation.objects.get(id=operation_id)
        self.assertEqual(operation.status, 'error')
        self.assertEqual(operation.error_message, 'Connection timeout to S3 storage')
        
        # Проверяем, что статус в ответе API — FAILED
        self.assertEqual(response.data['status'], 'FAILED')

    def test_4_attempt_to_complete_again(self):
        """Тест 4: Попытка повторного завершения."""
        # Создаём операцию
        create_response = self.client.post(
            self.create_url,
            self._create_payload(externalJobId='JOB-RETRY'),
            format='json'
        )
        operation_id = create_response.data['id']
        update_url = f'/api/backup-operations/{operation_id}/'
        
        # Сначала завершаем успешно
        self.client.patch(
            update_url,
            {
                'status': 'SUCCESS',
                'finishedAt': '2026-07-09T10:30:00Z'
            },
            format='json'
        )
        
        # Пытаемся изменить статус снова
        response = self.client.patch(
            update_url,
            {
                'status': 'FAILED',
                'errorMessage': 'Late error'
            },
            format='json'
        )
        
        # Ожидаем ошибку 400
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_5_nonexistent_configuration(self):
        """Тест 5: Несуществующая конфигурация."""
        response = self.client.post(
            self.create_url,
            self._create_payload(backupConfigurationId=9999),
            format='json'
        )
        
        # Ожидаем ошибку 400
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('backupConfigurationId', response.data)