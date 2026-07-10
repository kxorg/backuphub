from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from ..models import (
    SystemType, Environment, BackupTool,
    TargetSystem, TargetSystemVersion,
    BackupConfiguration, BackupConfigurationVersion,
    BackupOperation
)


# ==========================================
# Справочники (Dictionaries)
# ==========================================

class SystemTypeModelTest(TestCase):
    def setUp(self):
        self.system_type = SystemType.objects.create(
            name='PostgreSQL',
            description='Relational database',
            created_by='admin'
        )

    def test_system_type_creation(self):
        self.assertEqual(self.system_type.name, 'PostgreSQL')
        self.assertEqual(self.system_type.description, 'Relational database')
        self.assertEqual(self.system_type.created_by, 'admin')
        self.assertIsNotNone(self.system_type.created_at)

    def test_system_type_str(self):
        self.assertEqual(str(self.system_type), 'PostgreSQL')

    def test_system_type_unique_name(self):
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            SystemType.objects.create(name='PostgreSQL')

    def test_system_type_ordering(self):
        SystemType.objects.create(name='MySQL')
        SystemType.objects.create(name='GitLab')
        names = list(SystemType.objects.values_list('name', flat=True))
        self.assertEqual(names, sorted(names))

    def test_system_type_meta(self):
        self.assertEqual(SystemType._meta.verbose_name, 'System Type')
        self.assertEqual(SystemType._meta.verbose_name_plural, 'System Types')


class EnvironmentModelTest(TestCase):
    def setUp(self):
        self.environment = Environment.objects.create(
            name='Production',
            description='Live environment',
            created_by='admin'
        )

    def test_environment_creation(self):
        self.assertEqual(self.environment.name, 'Production')
        self.assertEqual(str(self.environment), 'Production')

    def test_environment_unique_name(self):
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Environment.objects.create(name='Production')

    def test_environment_ordering(self):
        Environment.objects.create(name='Development')
        Environment.objects.create(name='Staging')
        names = list(Environment.objects.values_list('name', flat=True))
        self.assertEqual(names, sorted(names))


class BackupToolModelTest(TestCase):
    def setUp(self):
        self.backup_tool = BackupTool.objects.create(
            name='pg_dump',
            description='PostgreSQL backup tool',
            is_active=True,
            created_by='admin'
        )

    def test_backup_tool_creation(self):
        self.assertEqual(self.backup_tool.name, 'pg_dump')
        self.assertTrue(self.backup_tool.is_active)
        self.assertEqual(str(self.backup_tool), 'pg_dump')

    def test_backup_tool_default_active(self):
        tool = BackupTool.objects.create(name='rsync')
        self.assertTrue(tool.is_active)

    def test_backup_tool_unique_name(self):
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            BackupTool.objects.create(name='pg_dump')


# ==========================================
# Target System & Version
# ==========================================

class TargetSystemModelTest(TestCase):
    def setUp(self):
        self.system_type = SystemType.objects.create(name='PostgreSQL')
        self.environment = Environment.objects.create(name='Production')
        self.target_system = TargetSystem.objects.create(
            system_type=self.system_type,
            environment=self.environment,
            name='DB Server 1',
            description='Main database',
            created_by='admin'
        )
        self.version = TargetSystemVersion.objects.create(
            target_system=self.target_system,
            version_number=1,
            owner='John Doe',
            administrator='Jane Smith',
            is_current=True,
            valid_from=timezone.now(),
            created_by='admin'
        )

    def test_target_system_creation(self):
        self.assertEqual(self.target_system.name, 'DB Server 1')
        self.assertTrue(self.target_system.is_active)
        self.assertIsNotNone(self.target_system.api_key)

    def test_target_system_str(self):
        self.assertEqual(str(self.target_system), 'DB Server 1')

    def test_target_system_api_key_unique(self):
        ts2 = TargetSystem.objects.create(
            system_type=self.system_type,
            name='DB Server 2'
        )
        self.assertNotEqual(self.target_system.api_key, ts2.api_key)

    def test_target_system_default_active(self):
        ts = TargetSystem.objects.create(
            system_type=self.system_type,
            name='New System'
        )
        self.assertTrue(ts.is_active)

    def test_current_version_property(self):
        self.assertEqual(self.target_system.current_version, self.version)
        self.assertEqual(self.target_system.current_version.owner, 'John Doe')

    def test_current_version_none(self):
        self.version.is_current = False
        self.version.save()
        self.assertIsNone(self.target_system.current_version)

    def test_environment_optional(self):
        ts = TargetSystem.objects.create(
            system_type=self.system_type,
            name='System without env'
        )
        self.assertIsNone(ts.environment)


class TargetSystemVersionModelTest(TestCase):
    def setUp(self):
        self.system_type = SystemType.objects.create(name='PostgreSQL')
        self.target_system = TargetSystem.objects.create(
            system_type=self.system_type,
            name='DB Server 1'
        )
        self.version1 = TargetSystemVersion.objects.create(
            target_system=self.target_system,
            version_number=1,
            owner='John',
            is_current=False,
            valid_from=timezone.now() - timedelta(days=10),
            valid_to=timezone.now() - timedelta(days=5),
            created_by='admin'
        )
        self.version2 = TargetSystemVersion.objects.create(
            target_system=self.target_system,
            version_number=2,
            owner='Jane',
            is_current=True,
            valid_from=timezone.now() - timedelta(days=5),
            created_by='admin'
        )

    def test_version_str(self):
        self.assertEqual(str(self.version1), 'DB Server 1 v1')

    def test_version_ordering(self):
        versions = list(TargetSystemVersion.objects.filter(
            target_system=self.target_system
        ).values_list('version_number', flat=True))
        self.assertEqual(versions, [2, 1])

    def test_version_unique_together(self):
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            TargetSystemVersion.objects.create(
                target_system=self.target_system,
                version_number=1,
                valid_from=timezone.now()
            )

    def test_version_cascade_delete(self):
        self.target_system.delete()
        self.assertEqual(TargetSystemVersion.objects.count(), 0)


# ==========================================
# Backup Configuration & Version
# ==========================================

class BackupConfigurationModelTest(TestCase):
    def setUp(self):
        self.system_type = SystemType.objects.create(name='PostgreSQL')
        self.target_system = TargetSystem.objects.create(
            system_type=self.system_type,
            name='DB Server 1'
        )
        self.version = TargetSystemVersion.objects.create(
            target_system=self.target_system,
            version_number=1,
            is_current=True,
            valid_from=timezone.now()
        )
        self.config = BackupConfiguration.objects.create(
            target_system_version=self.version,
            name='Daily Backup',
            description='Daily backup configuration',
            created_by='admin'
        )

    def test_backup_configuration_creation(self):
        self.assertEqual(self.config.name, 'Daily Backup')
        self.assertTrue(self.config.is_active)

    def test_backup_configuration_str(self):
        expected = 'Daily Backup (DB Server 1)'
        self.assertEqual(str(self.config), expected)

    def test_backup_configuration_default_active(self):
        config = BackupConfiguration.objects.create(
            target_system_version=self.version,
            name='New Config'
        )
        self.assertTrue(config.is_active)

    def test_current_version_property(self):
        config_version = BackupConfigurationVersion.objects.create(
            backup_configuration=self.config,
            backup_tool=BackupTool.objects.create(name='pg_dump'),
            version_number=1,
            is_current=True,
            valid_from=timezone.now()
        )
        self.assertEqual(self.config.current_version, config_version)


class BackupConfigurationVersionModelTest(TestCase):
    def setUp(self):
        self.system_type = SystemType.objects.create(name='PostgreSQL')
        self.backup_tool = BackupTool.objects.create(name='pg_dump')
        self.target_system = TargetSystem.objects.create(
            system_type=self.system_type,
            name='DB Server 1'
        )
        self.ts_version = TargetSystemVersion.objects.create(
            target_system=self.target_system,
            version_number=1,
            is_current=True,
            valid_from=timezone.now()
        )
        self.config = BackupConfiguration.objects.create(
            target_system_version=self.ts_version,
            name='Daily Backup'
        )
        self.config_version = BackupConfigurationVersion.objects.create(
            backup_configuration=self.config,
            backup_tool=self.backup_tool,
            version_number=1,
            backup_mode='full',
            schedule_cron='0 2 * * *',
            retention_days=30,
            rpo_minutes=1440,
            rto_minutes=60,
            storage_type='local',
            storage_path='/backup',
            is_current=True,
            valid_from=timezone.now(),
            created_by='admin'
        )

    def test_config_version_creation(self):
        self.assertEqual(self.config_version.version_number, 1)
        self.assertEqual(self.config_version.backup_mode, 'full')
        self.assertTrue(self.config_version.is_current)

    def test_config_version_str(self):
        expected = 'Daily Backup v1 (pg_dump)'
        self.assertEqual(str(self.config_version), expected)

    def test_config_version_defaults(self):
        cv = BackupConfigurationVersion.objects.create(
            backup_configuration=self.config,
            backup_tool=self.backup_tool,
            version_number=2,
            valid_from=timezone.now()
        )
        self.assertEqual(cv.backup_mode, 'full')
        self.assertEqual(cv.retention_days, 30)
        self.assertEqual(cv.rpo_minutes, 1440)
        self.assertEqual(cv.rto_minutes, 60)
        self.assertEqual(cv.storage_type, 'local')
        self.assertFalse(cv.verify_after_backup)
        self.assertFalse(cv.immutable_storage)

    def test_config_version_unique_together(self):
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            BackupConfigurationVersion.objects.create(
                backup_configuration=self.config,
                backup_tool=self.backup_tool,
                version_number=1,
                valid_from=timezone.now()
            )

    def test_config_version_cascade_delete(self):
        self.config.delete()
        self.assertEqual(BackupConfigurationVersion.objects.count(), 0)

    def test_backup_mode_choices(self):
        choices = [c[0] for c in BackupConfigurationVersion.BACKUP_MODE_CHOICES]
        self.assertIn('full', choices)
        self.assertIn('incremental', choices)
        self.assertIn('differential', choices)

    def test_storage_type_choices(self):
        choices = [c[0] for c in BackupConfigurationVersion.STORAGE_TYPE_CHOICES]
        self.assertIn('local', choices)
        self.assertIn('s3', choices)
        self.assertIn('azure', choices)


# ==========================================
# Backup Operation
# ==========================================

class BackupOperationModelTest(TestCase):
    def setUp(self):
        self.system_type = SystemType.objects.create(name='PostgreSQL')
        self.backup_tool = BackupTool.objects.create(name='pg_dump')
        self.target_system = TargetSystem.objects.create(
            system_type=self.system_type,
            name='DB Server 1'
        )
        self.ts_version = TargetSystemVersion.objects.create(
            target_system=self.target_system,
            version_number=1,
            is_current=True,
            valid_from=timezone.now()
        )
        self.config = BackupConfiguration.objects.create(
            target_system_version=self.ts_version,
            name='Daily Backup'
        )
        self.config_version = BackupConfigurationVersion.objects.create(
            backup_configuration=self.config,
            backup_tool=self.backup_tool,
            version_number=1,
            is_current=True,
            valid_from=timezone.now()
        )
        self.operation = BackupOperation.objects.create(
            backup_configuration_version=self.config_version,
            hostname='db-server-1',
            ip_address='192.168.1.100',
            status='success',
            started_at=timezone.now() - timedelta(hours=1),
            finished_at=timezone.now(),
            size_bytes=1073741824,  # 1 GB
            storage_type='local',
            storage_path='/backup/db.sql',
            created_by='system'
        )

    def test_operation_creation(self):
        self.assertEqual(self.operation.hostname, 'db-server-1')
        self.assertEqual(self.operation.status, 'success')

    def test_operation_str(self):
        expected = f'Operation #{self.operation.id} - success (db-server-1)'
        self.assertEqual(str(self.operation), expected)

    def test_duration_seconds(self):
        self.assertIsNotNone(self.operation.duration_seconds)
        self.assertGreater(self.operation.duration_seconds, 0)
        self.assertEqual(self.operation.duration_seconds, 3600)

    def test_duration_none_when_no_finished(self):
        self.operation.finished_at = None
        self.operation.save()
        self.assertIsNone(self.operation.duration_seconds)

    def test_duration_none_when_no_started(self):
        self.operation.started_at = None
        # self.operation.save()
        self.assertIsNone(self.operation.duration_seconds)

    def test_size_human_gb(self):
        self.assertEqual(self.operation.size_human, '1.0 GB')

    def test_size_human_mb(self):
        self.operation.size_bytes = 1048576
        self.assertEqual(self.operation.size_human, '1.0 MB')

    def test_size_human_kb(self):
        self.operation.size_bytes = 2048
        self.assertEqual(self.operation.size_human, '2.0 KB')

    def test_size_human_bytes(self):
        self.operation.size_bytes = 500
        self.assertEqual(self.operation.size_human, '500.0 B')

    def test_size_human_none(self):
        self.operation.size_bytes = None
        self.assertIsNone(self.operation.size_human)

    def test_size_human_tb(self):
        self.operation.size_bytes = 1099511627776  # 1 TB
        self.assertEqual(self.operation.size_human, '1.0 TB')

    def test_status_choices(self):
        choices = [c[0] for c in BackupOperation.STATUS_CHOICES]
        self.assertIn('success', choices)
        self.assertIn('error', choices)
        self.assertIn('in_progress', choices)
        self.assertIn('warning', choices)
        self.assertIn('cancelled', choices)

    def test_operation_ordering(self):
        op2 = BackupOperation.objects.create(
            backup_configuration_version=self.config_version,
            hostname='db-server-2',
            status='success',
            started_at=timezone.now(),
            finished_at=timezone.now() + timedelta(hours=1)
        )
        first = BackupOperation.objects.first()
        self.assertEqual(first.id, op2.id)

    def test_operation_optional_fields(self):
        op = BackupOperation.objects.create(
            backup_configuration_version=self.config_version,
            hostname='test-server',
            status='in_progress',
            started_at=timezone.now()
        )
        self.assertIsNone(op.ip_address)
        self.assertIsNone(op.finished_at)
        self.assertIsNone(op.size_bytes)
        self.assertIsNone(op.metadata)
        self.assertIsNone(op.error_message)