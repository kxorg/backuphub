from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import User
from datetime import timedelta
from ..models import (
    SystemType, Environment, BackupTool,
    TargetSystem, TargetSystemVersion,
    BackupConfiguration, BackupConfigurationVersion,
    BackupOperation
)


class BaseAuthTestCase(TestCase):
    """Базовый класс с авторизацией для тестов вьюх"""
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
        
        self.system_type = SystemType.objects.create(name='PostgreSQL')
        self.environment = Environment.objects.create(name='Production')
        self.backup_tool = BackupTool.objects.create(name='pg_dump')
        
        self.target_system = TargetSystem.objects.create(
            system_type=self.system_type,
            environment=self.environment,
            name='DB Server 1',
            created_by='testuser'
        )
        self.ts_version = TargetSystemVersion.objects.create(
            target_system=self.target_system,
            version_number=1,
            owner='John',
            administrator='Jane',
            is_current=True,
            valid_from=timezone.now(),
            created_by='testuser'
        )
        self.config = BackupConfiguration.objects.create(
            target_system_version=self.ts_version,
            name='Daily Backup',
            created_by='testuser'
        )
        self.config_version = BackupConfigurationVersion.objects.create(
            backup_configuration=self.config,
            backup_tool=self.backup_tool,
            version_number=1,
            backup_mode='full',
            retention_days=30,
            rpo_minutes=1440,
            rto_minutes=60,
            storage_type='local',
            is_current=True,
            valid_from=timezone.now(),
            created_by='testuser'
        )


# ==========================================
# Target System Views
# ==========================================

class TargetSystemViewsTest(BaseAuthTestCase):
    def test_list_view(self):
        response = self.client.get(reverse('target_systems:target_system_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'DB Server 1')

    def test_detail_view(self):
        response = self.client.get(
            reverse('target_systems:target_system_detail', args=[self.target_system.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'DB Server 1')

    def test_create_view_get(self):
        response = self.client.get(reverse('target_systems:target_system_create'))
        self.assertEqual(response.status_code, 200)

    def test_create_view_post(self):
        data = {
            'system_type': self.system_type.id,
            'environment': self.environment.id,
            'name': 'New Server',
            'description': 'Test server',
            'owner': 'John Doe',
            'administrator': 'Jane Smith',
            'is_active': True
        }
        response = self.client.post(reverse('target_systems:target_system_create'), data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(TargetSystem.objects.filter(name='New Server').exists())
        self.assertEqual(TargetSystemVersion.objects.count(), 2)

    def test_create_view_creates_first_version(self):
        data = {
            'system_type': self.system_type.id,
            'name': 'New Server',
            'owner': 'Owner',
            'administrator': 'Admin',
            'is_active': True
        }
        self.client.post(reverse('target_systems:target_system_create'), data)
        ts = TargetSystem.objects.get(name='New Server')
        version = TargetSystemVersion.objects.get(target_system=ts, version_number=1)
        self.assertTrue(version.is_current)
        self.assertEqual(version.owner, 'Owner')

    def test_update_view_get(self):
        response = self.client.get(
            reverse('target_systems:target_system_edit', args=[self.target_system.id])
        )
        self.assertEqual(response.status_code, 200)

    def test_update_view_post_no_version_change(self):
        data = {
            'system_type': self.system_type.id,
            'environment': self.environment.id,
            'name': 'DB Server 1 Updated',
            'description': 'Updated description',
            'owner': 'John',
            'administrator': 'Jane',
            'is_active': True
        }
        response = self.client.post(
            reverse('target_systems:target_system_edit', args=[self.target_system.id]),
            data
        )
        self.assertEqual(response.status_code, 302)
        self.target_system.refresh_from_db()
        self.assertEqual(self.target_system.name, 'DB Server 1 Updated')
        self.assertEqual(TargetSystemVersion.objects.count(), 1)

    def test_update_view_post_with_version_change(self):
        data = {
            'system_type': self.system_type.id,
            'name': 'DB Server 1',
            'owner': 'New Owner',
            'administrator': 'New Admin',
            'is_active': True
        }
        response = self.client.post(
            reverse('target_systems:target_system_edit', args=[self.target_system.id]),
            data
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(TargetSystemVersion.objects.count(), 2)
        new_version = TargetSystemVersion.objects.filter(
            target_system=self.target_system,
            version_number=2
        ).first()
        self.assertIsNotNone(new_version)
        self.assertEqual(new_version.owner, 'New Owner')
        self.assertTrue(new_version.is_current)

    def test_update_view_closes_previous_version(self):
        data = {
            'system_type': self.system_type.id,
            'name': 'DB Server 1',
            'owner': 'New Owner',
            'administrator': 'Jane',
            'is_active': True
        }
        self.client.post(
            reverse('target_systems:target_system_edit', args=[self.target_system.id]),
            data
        )
        old_version = TargetSystemVersion.objects.get(version_number=1)
        self.assertFalse(old_version.is_current)
        self.assertIsNotNone(old_version.valid_to)

    def test_delete_view_post(self):
        response = self.client.post(
            reverse('target_systems:target_system_delete', args=[self.target_system.id])
        )
        self.assertEqual(response.status_code, 302)
        self.target_system.refresh_from_db()
        self.assertFalse(self.target_system.is_active)

    def test_delete_view_get_redirects(self):
        response = self.client.get(
            reverse('target_systems:target_system_delete', args=[self.target_system.id])
        )
        self.assertEqual(response.status_code, 302)

    def test_history_view(self):
        response = self.client.get(
            reverse('target_systems:target_system_history', args=[self.target_system.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'v1')

    def test_version_detail_view(self):
        response = self.client.get(
            reverse('target_systems:target_system_version_detail', 
                    args=[self.target_system.id, self.ts_version.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'John')

    def test_version_detail_readonly(self):
        response = self.client.get(
            reverse('target_systems:target_system_version_detail', 
                    args=[self.target_system.id, self.ts_version.id])
        )
        self.assertTrue(response.context['is_readonly'])


# ==========================================
# Backup Configuration Views
# ==========================================

class BackupConfigurationViewsTest(BaseAuthTestCase):
    def test_list_view(self):
        response = self.client.get(reverse('backup_configuration_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Daily Backup')

    def test_detail_view(self):
        response = self.client.get(
            reverse('backup_configuration_detail', args=[self.config.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Daily Backup')

    def test_create_view_get(self):
        response = self.client.get(reverse('backup_configuration_create'))
        self.assertEqual(response.status_code, 200)

    def test_create_view_post(self):
        data = {
            'target_system_version': self.ts_version.id,
            'name': 'Weekly Backup',
            'description': 'Weekly backup',
            'backup_tool': self.backup_tool.id,
            'backup_mode': 'incremental',
            'schedule_cron': '0 3 * * 0',
            'retention_days': 60,
            'rpo_minutes': 10080,
            'rto_minutes': 120,
            'storage_type': 's3',
            'storage_path': 's3://bucket/backups',
            'verify_after_backup': True,
            'immutable_storage': False,
            'is_active': True
        }
        response = self.client.post(reverse('backup_configuration_create'), data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            BackupConfiguration.objects.filter(name='Weekly Backup').exists()
        )

    def test_create_view_creates_first_version(self):
        data = {
            'target_system_version': self.ts_version.id,
            'name': 'New Config',
            'backup_tool': self.backup_tool.id,
            'backup_mode': 'full',
            'retention_days': 30,
            'rpo_minutes': 1440,
            'rto_minutes': 60,
            'storage_type': 'local',
            'is_active': True
        }
        self.client.post(reverse('backup_configuration_create'), data)
        config = BackupConfiguration.objects.get(name='New Config')
        version = BackupConfigurationVersion.objects.get(
            backup_configuration=config, version_number=1
        )
        self.assertTrue(version.is_current)

    def test_update_view_get(self):
        response = self.client.get(
            reverse('backup_configuration_edit', args=[self.config.id])
        )
        self.assertEqual(response.status_code, 200)

    def test_update_view_post_no_version_change(self):
        data = {
            'target_system_version': self.ts_version.id,
            'name': 'Daily Backup Updated',
            'description': 'Updated',
            'backup_tool': self.backup_tool.id,
            'backup_mode': 'full',
            'schedule_cron': '0 2 * * *',
            'retention_days': 30,
            'rpo_minutes': 1440,
            'rto_minutes': 60,
            'storage_type': 'local',
            'storage_path': '/backup',
            'verify_after_backup': False,
            'immutable_storage': False,
            'is_active': True
        }
        response = self.client.post(
            reverse('backup_configuration_edit', args=[self.config.id]),
            data
        )
        self.assertEqual(response.status_code, 302)
        self.config.refresh_from_db()
        self.assertEqual(self.config.name, 'Daily Backup Updated')
        self.assertEqual(BackupConfigurationVersion.objects.count(), 1)

    def test_update_view_post_with_version_change(self):
        data = {
            'target_system_version': self.ts_version.id,
            'name': 'Daily Backup',
            'backup_tool': self.backup_tool.id,
            'backup_mode': 'incremental',
            'retention_days': 30,
            'rpo_minutes': 1440,
            'rto_minutes': 60,
            'storage_type': 'local',
            'is_active': True
        }
        response = self.client.post(
            reverse('backup_configuration_edit', args=[self.config.id]),
            data
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(BackupConfigurationVersion.objects.count(), 2)

    def test_update_view_closes_previous_version(self):
        data = {
            'target_system_version': self.ts_version.id,
            'name': 'Daily Backup',
            'backup_tool': self.backup_tool.id,
            'backup_mode': 'incremental',
            'retention_days': 30,
            'rpo_minutes': 1440,
            'rto_minutes': 60,
            'storage_type': 'local',
            'is_active': True
        }
        self.client.post(
            reverse('backup_configuration_edit', args=[self.config.id]),
            data
        )
        old_version = BackupConfigurationVersion.objects.get(version_number=1)
        self.assertFalse(old_version.is_current)
        self.assertIsNotNone(old_version.valid_to)

    def test_delete_view_post(self):
        response = self.client.post(
            reverse('backup_configuration_delete', args=[self.config.id])
        )
        self.assertEqual(response.status_code, 302)
        self.config.refresh_from_db()
        self.assertFalse(self.config.is_active)

    def test_delete_view_get_redirects(self):
        response = self.client.get(
            reverse('backup_configuration_delete', args=[self.config.id])
        )
        self.assertEqual(response.status_code, 302)

    def test_history_view(self):
        response = self.client.get(
            reverse('backup_configuration_history', args=[self.config.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'v1')

    def test_version_detail_view(self):
        response = self.client.get(
            reverse('backup_configuration_version_detail', 
                    args=[self.config.id, self.config_version.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_readonly'])


# ==========================================
# Backup Operation Views
# ==========================================

class BackupOperationViewsTest(BaseAuthTestCase):
    def setUp(self):
        super().setUp()
        self.operation = BackupOperation.objects.create(
            backup_configuration_version=self.config_version,
            hostname='db-server-1',
            ip_address='192.168.1.100',
            status='success',
            started_at=timezone.now() - timedelta(hours=1),
            finished_at=timezone.now(),
            size_bytes=1073741824,
            created_by='system'
        )

    def test_list_view(self):
        response = self.client.get(reverse('backup_operation_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'db-server-1')

    def test_list_view_search(self):
        response = self.client.get(
            reverse('backup_operation_list') + '?q=db-server'
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'db-server-1')

    def test_list_view_search_no_results(self):
        response = self.client.get(
            reverse('backup_operation_list') + '?q=nonexistent'
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'db-server-1')

    def test_list_view_filter_status(self):
        response = self.client.get(
            reverse('backup_operation_list') + '?status=success'
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'db-server-1')

    def test_list_view_filter_hostname(self):
        response = self.client.get(
            reverse('backup_operation_list') + '?hostname=db-server'
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'db-server-1')

    def test_list_view_filter_configuration(self):
        response = self.client.get(
            reverse('backup_operation_list') + f'?configuration={self.config.id}'
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'db-server-1')

    def test_list_view_context(self):
        response = self.client.get(reverse('backup_operation_list'))
        self.assertIn('search_query', response.context)
        self.assertIn('status_filter', response.context)
        self.assertIn('hostname_filter', response.context)
        self.assertIn('configuration_filter', response.context)
        self.assertIn('status_choices', response.context)

    def test_detail_view(self):
        response = self.client.get(
            reverse('backup_operation_detail', args=[self.operation.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'db-server-1')
        self.assertContains(response, '1.0 GB')

    def test_detail_view_context(self):
        response = self.client.get(
            reverse('backup_operation_detail', args=[self.operation.id])
        )
        self.assertIn('duration_seconds', response.context)
        self.assertIn('size_human', response.context)
        self.assertEqual(response.context['size_human'], '1.0 GB')


# ==========================================
# Dictionary Views
# ==========================================

class SystemTypeViewsTest(BaseAuthTestCase):
    def test_list_view(self):
        response = self.client.get(reverse('dictionaries:system_type_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'PostgreSQL')

    def test_create_view_get(self):
        response = self.client.get(reverse('dictionaries:system_type_create'))
        self.assertEqual(response.status_code, 200)

    def test_create_view_post(self):
        data = {'name': 'MySQL', 'description': 'MySQL database'}
        response = self.client.post(reverse('dictionaries:system_type_create'), data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(SystemType.objects.filter(name='MySQL').exists())

    def test_update_view_get(self):
        st = SystemType.objects.create(name='MySQL')
        response = self.client.get(reverse('dictionaries:system_type_edit', args=[st.id]))
        self.assertEqual(response.status_code, 200)

    def test_update_view_post(self):
        st = SystemType.objects.create(name='PostgreSQL')
        data = {'name': 'PostgreSQL Updated', 'description': 'Updated'}
        response = self.client.post(
            reverse('dictionaries:system_type_edit', args=[st.id]),
            data
        )
        self.assertEqual(response.status_code, 302)
        st.refresh_from_db()
        self.assertEqual(st.name, 'PostgreSQL Updated')

    def test_delete_view_post(self):
        st = SystemType.objects.create(name='ToDelete')
        response = self.client.post(reverse('dictionaries:system_type_delete', args=[st.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(SystemType.objects.filter(id=st.id).exists())

    def test_delete_view_get(self):
        st = SystemType.objects.create(name='ToDelete')
        response = self.client.get(reverse('dictionaries:system_type_delete', args=[st.id]))
        self.assertEqual(response.status_code, 200)


class EnvironmentViewsTest(BaseAuthTestCase):
    def test_list_view(self):
        response = self.client.get(reverse('dictionaries:environment_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Production')

    def test_create_view_post(self):
        data = {'name': 'Staging', 'description': 'Staging environment'}
        response = self.client.post(reverse('dictionaries:environment_create'), data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Environment.objects.filter(name='Staging').exists())

    def test_update_view_post(self):
        env = Environment.objects.create(name='Test')
        data = {'name': 'Test Updated', 'description': 'Updated'}
        response = self.client.post(
            reverse('dictionaries:environment_edit', args=[env.id]),
            data
        )
        self.assertEqual(response.status_code, 302)
        env.refresh_from_db()
        self.assertEqual(env.name, 'Test Updated')

    def test_delete_view_post(self):
        env = Environment.objects.create(name='ToDelete')
        response = self.client.post(reverse('dictionaries:environment_delete', args=[env.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Environment.objects.filter(id=env.id).exists())


class BackupToolViewsTest(BaseAuthTestCase):
    def test_list_view(self):
        response = self.client.get(reverse('dictionaries:backup_tool_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'pg_dump')

    def test_create_view_post(self):
        data = {
            'name': 'Velero',
            'description': 'Kubernetes backup',
            'is_active': True
        }
        response = self.client.post(reverse('dictionaries:backup_tool_create'), data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(BackupTool.objects.filter(name='Velero').exists())

    def test_update_view_post(self):
        tool = BackupTool.objects.create(name='rsync')
        data = {'name': 'rsync Updated', 'description': 'Updated', 'is_active': True}
        response = self.client.post(
            reverse('dictionaries:backup_tool_edit', args=[tool.id]),
            data
        )
        self.assertEqual(response.status_code, 302)
        tool.refresh_from_db()
        self.assertEqual(tool.name, 'rsync Updated')

    def test_delete_view_post(self):
        tool = BackupTool.objects.create(name='ToDelete')
        response = self.client.post(reverse('dictionaries:backup_tool_delete', args=[tool.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(BackupTool.objects.filter(id=tool.id).exists())


# ==========================================
# Authentication Tests
# ==========================================

class AuthenticationTest(TestCase):
    """Тесты проверки авторизации для всех вьюх"""
    def setUp(self):
        self.system_type = SystemType.objects.create(name='PostgreSQL')
        self.target_system = TargetSystem.objects.create(
            system_type=self.system_type,
            name='DB Server 1'
        )

    def test_target_system_list_requires_login(self):
        response = self.client.get(reverse('target_systems:target_system_list'))
        self.assertEqual(response.status_code, 302)

    def test_target_system_detail_requires_login(self):
        response = self.client.get(
            reverse('target_systems:target_system_detail', args=[self.target_system.id])
        )
        self.assertEqual(response.status_code, 302)

    def test_backup_configuration_list_requires_login(self):
        response = self.client.get(reverse('backup_configuration_list'))
        self.assertEqual(response.status_code, 302)

    def test_backup_operation_list_requires_login(self):
        response = self.client.get(reverse('backup_operation_list'))
        self.assertEqual(response.status_code, 302)

    def test_system_type_list_requires_login(self):
        response = self.client.get(reverse('dictionaries:system_type_list'))
        self.assertEqual(response.status_code, 302)

    def test_environment_list_requires_login(self):
        response = self.client.get(reverse('dictionaries:environment_list'))
        self.assertEqual(response.status_code, 302)

    def test_backup_tool_list_requires_login(self):
        response = self.client.get(reverse('dictionaries:backup_tool_list'))
        self.assertEqual(response.status_code, 302)


# ==========================================
# Index View Test
# ==========================================

class IndexViewTest(BaseAuthTestCase):
    def test_index_view(self):
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'BackupHub')

    def test_index_context(self):
        response = self.client.get(reverse('index'))
        self.assertIn('total_systems', response.context)
        self.assertIn('total_backups', response.context)
        self.assertIn('recent_backups', response.context)
        self.assertIn('systems_data', response.context)
        self.assertIn('success_24h', response.context)
        self.assertIn('error_24h', response.context)

    def test_index_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 302)


# ==========================================
# Pagination Tests
# ==========================================

class PaginationTest(BaseAuthTestCase):
    def test_target_system_pagination(self):
        for i in range(25):
            TargetSystem.objects.create(
                system_type=self.system_type,
                name=f'System {i}'
            )
        response = self.client.get(reverse('target_systems:target_system_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_paginated'])
        self.assertEqual(len(response.context['target_systems']), 20)

    def test_backup_operation_pagination(self):
        for i in range(55):
            BackupOperation.objects.create(
                backup_configuration_version=self.config_version,
                hostname=f'server-{i}',
                status='success',
                started_at=timezone.now() - timedelta(hours=i),
                finished_at=timezone.now() - timedelta(hours=i-1),
                size_bytes=1024
            )
        response = self.client.get(reverse('backup_operation_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_paginated'])
        self.assertEqual(len(response.context['operations']), 50)

    def test_system_type_pagination(self):
        for i in range(55):
            SystemType.objects.create(name=f'Type {i}')
        response = self.client.get(reverse('dictionaries:system_type_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_paginated'])
        self.assertEqual(len(response.context['system_types']), 50)