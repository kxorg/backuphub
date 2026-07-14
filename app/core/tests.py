from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone

from .models import (
    SystemType, Environment, BackupTool, 
    TargetSystem, TargetSystemVersion, 
    BackupConfiguration, BackupConfigurationVersion, 
    BackupOperation
)
from .serializers import TargetSystemCreateSerializer, BackupConfigurationCreateSerializer


class BaseTestCase(TestCase):
    """Базовый класс с общими фикстурами (setUpTestData для ускорения)"""
    
    @classmethod
    def setUpTestData(cls):
        # Пользователь
        cls.user = User.objects.create_user(username='testuser', password='password123')
        
        # Справочники
        cls.system_type = SystemType.objects.create(name='PostgreSQL', description='DB')
        cls.environment = Environment.objects.create(name='Production', description='Prod')
        cls.backup_tool = BackupTool.objects.create(name='pg_dump', description='Tool')
        
        # Target System с версией 1
        cls.target_system = TargetSystem.objects.create(
            system_type=cls.system_type,
            environment=cls.environment,
            name='DB-Server-01',
            created_by=cls.user.username
        )
        cls.ts_version_1 = TargetSystemVersion.objects.create(
            target_system=cls.target_system,
            version_number=1,
            owner='John Doe',
            administrator='Admin Team',
            is_current=True,
            valid_from=timezone.now(),
            created_by=cls.user.username
        )
        
        # Backup Configuration с версией 1
        cls.backup_config = BackupConfiguration.objects.create(
            target_system_version=cls.ts_version_1,
            name='Daily Full Backup',
            created_by=cls.user.username
        )
        cls.bc_version_1 = BackupConfigurationVersion.objects.create(
            backup_configuration=cls.backup_config,
            version_number=1,
            backup_tool=cls.backup_tool,
            backup_mode='full',
            retention_days=30,
            rpo_minutes=1440,
            rto_minutes=60,
            storage_type='local',
            is_current=True,
            valid_from=timezone.now(),
            created_by=cls.user.username
        )

    def setUp(self):
        self.client = Client()
        self.client.login(username='testuser', password='password123')


class TestModelProperties(BaseTestCase):
    """Тесты вычисляемых свойств моделей"""

    def test_backup_operation_duration_seconds(self):
        start = timezone.now() - timedelta(minutes=15, seconds=30)
        finish = timezone.now()
        op = BackupOperation.objects.create(
            backup_configuration_version=self.bc_version_1,
            started_at=start,
            finished_at=finish,
            status='success'
        )
        self.assertEqual(op.duration_seconds, 930)

    def test_backup_operation_duration_in_progress(self):
        op = BackupOperation.objects.create(
            backup_configuration_version=self.bc_version_1,
            started_at=timezone.now(),
            finished_at=None,
            status='in_progress'
        )
        self.assertIsNone(op.duration_seconds)

    def test_backup_operation_size_human(self):
        op_bytes = BackupOperation.objects.create(
            backup_configuration_version=self.bc_version_1, size_bytes=500)
        self.assertEqual(op_bytes.size_human, "500.0 B")
        
        op_gb = BackupOperation.objects.create(
            backup_configuration_version=self.bc_version_1, size_bytes=5 * 1024 * 1024 * 1024)
        self.assertEqual(op_gb.size_human, "5.0 GB")
        
        op_none = BackupOperation.objects.create(
            backup_configuration_version=self.bc_version_1, size_bytes=None)
        self.assertIsNone(op_none.size_human)

    def test_current_version_property(self):
        self.assertEqual(self.target_system.current_version, self.ts_version_1)
        self.assertEqual(self.backup_config.current_version, self.bc_version_1)


class TestTargetSystemViews(BaseTestCase):
    """Тесты UI Views для TargetSystem и логики версионирования"""

    def test_login_required(self):
        self.client.logout()
        response = self.client.get(reverse('target_system_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_create_target_system_creates_version(self):
        url = reverse('target_system_create')
        data = {
            'system_type': self.system_type.id,
            'environment': self.environment.id,
            'name': 'New System',
            'description': 'Test',
            'is_active': True,
            'owner': 'Alice',
            'administrator': 'Bob',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        
        new_system = TargetSystem.objects.get(name='New System')
        self.assertEqual(new_system.versions.count(), 1)
        self.assertEqual(new_system.current_version.version_number, 1)
        self.assertEqual(new_system.current_version.owner, 'Alice')

    def test_update_versioned_fields_creates_new_version(self):
        url = reverse('target_system_edit', kwargs={'pk': self.target_system.pk})
        data = {
            'system_type': self.system_type.id,
            'environment': self.environment.id,
            'name': self.target_system.name,
            'description': self.target_system.description,
            'is_active': True,
            'owner': 'New Owner',  # Меняем versioned field
            'administrator': self.ts_version_1.administrator,
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        
        versions = TargetSystemVersion.objects.filter(target_system=self.target_system)
        self.assertEqual(versions.count(), 2)
        
        new_v = versions.filter(is_current=True).first()
        self.assertEqual(new_v.version_number, 2)
        self.assertEqual(new_v.owner, 'New Owner')
        
        old_v = versions.filter(version_number=1).first()
        self.assertFalse(old_v.is_current)
        self.assertIsNotNone(old_v.valid_to)

    def test_update_non_versioned_fields_no_new_version(self):
        url = reverse('target_system_edit', kwargs={'pk': self.target_system.pk})
        data = {
            'system_type': self.system_type.id,
            'environment': self.environment.id,
            'name': self.target_system.name,
            'description': 'Updated description', # Меняем НЕ versioned field
            'is_active': True,
            'owner': self.ts_version_1.owner,
            'administrator': self.ts_version_1.administrator,
        }
        self.client.post(url, data)
        
        versions = TargetSystemVersion.objects.filter(target_system=self.target_system)
        self.assertEqual(versions.count(), 1) # Версия не создалась

    def test_delete_deactivates_system(self):
        url = reverse('target_system_delete', kwargs={'pk': self.target_system.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        
        self.target_system.refresh_from_db()
        self.assertFalse(self.target_system.is_active)


class TestBackupConfigurationViews(BaseTestCase):
    """Тесты UI Views для BackupConfiguration"""

    def test_update_versioned_fields_creates_new_version(self):
        url = reverse('backup_configuration_edit', kwargs={'pk': self.backup_config.pk})
        data = {
            'target_system_version': self.ts_version_1.id,
            'name': self.backup_config.name,
            'description': self.backup_config.description,
            'is_active': True,
            'backup_tool': self.backup_tool.id,
            'backup_mode': 'incremental', # Меняем versioned field
            'schedule_cron': '0 0 * * *',
            'retention_days': 60,         # Меняем versioned field
            'rpo_minutes': 1440,
            'rto_minutes': 60,
            'storage_type': 'local',
            'storage_path': '',
            'verify_after_backup': False,
            'immutable_storage': False,
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        
        versions = BackupConfigurationVersion.objects.filter(backup_configuration=self.backup_config)
        self.assertEqual(versions.count(), 2)
        
        new_v = versions.filter(is_current=True).first()
        self.assertEqual(new_v.version_number, 2)
        self.assertEqual(new_v.backup_mode, 'incremental')
        self.assertEqual(new_v.retention_days, 60)


class TestSerializers(BaseTestCase):
    """Тесты REST API Сериализаторов"""

    def _get_mock_request(self):
        class MockRequest:
            user = self.user
        return MockRequest()

    def test_target_system_create_serializer(self):
        data = {
            'name': 'API System',
            'system_type': self.system_type.id,
            'environment': self.environment.id,
            'description': 'API desc',
            'owner': 'API Owner',
            'administrator': 'API Admin',
            'is_active': True
        }
        
        serializer = TargetSystemCreateSerializer(
            data=data, 
            context={'request': self._get_mock_request()}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        
        system = serializer.save()
        
        self.assertEqual(TargetSystem.objects.filter(name='API System').count(), 1)
        self.assertEqual(system.versions.count(), 1)
        self.assertEqual(system.current_version.owner, 'API Owner')
        self.assertEqual(system.current_version.created_by, self.user.username)

    def test_backup_configuration_create_serializer(self):
        data = {
            'name': 'API Backup Config',
            'target_system_version': self.ts_version_1.id,
            'description': 'API config desc',
            'is_active': True,
            'backup_tool': self.backup_tool.id,
            'backup_mode': 'incremental',
            'schedule_cron': '0 2 * * *',
            'retention_days': 15,
            'rpo_minutes': 60,
            'rto_minutes': 30,
            'storage_type': 's3',
            'storage_path': 's3://bucket/path',
            'verify_after_backup': True,
            'immutable_storage': False
        }
        
        serializer = BackupConfigurationCreateSerializer(
            data=data, 
            context={'request': self._get_mock_request()}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        
        config = serializer.save()
        
        self.assertEqual(BackupConfiguration.objects.filter(name='API Backup Config').count(), 1)
        self.assertEqual(config.versions.count(), 1)
        
        v = config.current_version
        self.assertEqual(v.version_number, 1)
        self.assertEqual(v.backup_mode, 'incremental')
        self.assertEqual(v.retention_days, 15)
        self.assertEqual(v.storage_type, 's3')
        self.assertTrue(v.verify_after_backup)