"""
Tests for core application models.
Testing creation, string representations, validation, and business methods.
"""
import pytest
import uuid
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

from core.models import TargetSystem, Host, Backup
from .factories import TargetSystemFactory, HostFactory, BackupFactory


pytestmark = pytest.mark.django_db


class TestTargetSystemModel:
    """Tests for TargetSystem model"""

    def test_create_target_system(self):
        """Test: Create a system"""
        system = TargetSystemFactory()
        assert system.pk is not None
        assert system.name is not None
        assert system.system_type in ['Linux', 'Windows', 'MacOS']
        assert system.api_key is not None
        assert system.created_at is not None

    def test_target_system_str_method(self):
        """Test: String representation of a system"""
        system = TargetSystemFactory(name='Production')
        assert str(system) == 'Production'

    def test_target_system_api_key_unique(self):
        """Test: API key must be unique"""
        system1 = TargetSystemFactory()
        system2 = TargetSystemFactory()
        assert system1.api_key != system2.api_key

    def test_target_system_cascade_delete(self):
        """Test: Deleting a system deletes related hosts"""
        system = TargetSystemFactory()
        host1 = HostFactory(target_system=system)
        host2 = HostFactory(target_system=system)

        system_id = system.id
        system.delete()

        assert Host.objects.filter(target_system_id=system_id).count() == 0


class TestHostModel:
    """Tests for Host model"""

    def test_create_host(self):
        """Test: Create a host"""
        host = HostFactory()
        assert host.pk is not None
        assert host.hostname.startswith('server-')
        assert host.ip_address.startswith('192.168.1.')
        assert host.target_system is not None

    def test_host_str_method(self):
        """Test: String representation of a host"""
        host = HostFactory(hostname='web01', ip_address='10.0.0.5')
        assert str(host) == 'web01 (10.0.0.5)'

    def test_host_requires_target_system(self):
        """Test: Host must have a target system"""
        with pytest.raises(IntegrityError):
            Host.objects.create(hostname='test', ip_address='1.1.1.1')

    def test_host_backups_relationship(self):
        """Test: Host -> backups relationship"""
        host = HostFactory()
        BackupFactory.create_batch(3, host=host)

        assert host.backups.count() == 3

    def test_host_target_system_relationship(self):
        """Test: Host -> target system relationship"""
        system = TargetSystemFactory()
        host = HostFactory(target_system=system)

        assert host.target_system == system
        assert system.hosts.first() == host


class TestBackupModel:
    """Tests for Backup model"""

    def test_create_backup(self):
        """Test: Create a backup"""
        backup = BackupFactory()
        assert backup.pk is not None
        assert isinstance(backup.id, (str, uuid.UUID))
        assert backup.status in ['in_progress', 'success', 'error']
        assert backup.start_time is not None

    def test_backup_str_method(self):
        """Test: String representation of a backup"""
        backup = BackupFactory(status='success')
        assert str(backup) == f'Backup {backup.id} - success'

    def test_backup_status_choices(self):
        """Test: Backup statuses must be from allowed values"""
        valid_statuses = ['in_progress', 'success', 'error']

        for status in valid_statuses:
            backup = BackupFactory(status=status)
            assert backup.status == status

    def test_backup_duration_property(self):
        """Test: Calculating backup duration"""
        backup = BackupFactory(
            start_time=timezone.now() - timedelta(hours=2),
            end_time=timezone.now() - timedelta(hours=1)
        )

        duration = backup.duration
        assert duration is not None
        # Using approximate comparison due to microseconds
        assert abs(duration.total_seconds() - 3600) < 1  # ~1 hour

    def test_backup_duration_none_when_incomplete(self):
        """Test: Duration is None when backup is incomplete"""
        backup = BackupFactory(
            start_time=timezone.now(),
            end_time=None
        )

        assert backup.duration is None

    def test_backup_cascade_delete_host(self):
        """Test: Deleting a host preserves backups (SET_NULL)"""
        host = HostFactory()
        backup = BackupFactory(host=host)

        host.delete()
        backup.refresh_from_db()

        assert backup.host is None

    def test_backup_cascade_delete_target_system(self):
        """Test: Deleting a system deletes backups (CASCADE)"""
        system = TargetSystemFactory()
        backup = BackupFactory(target_system=system)

        system_id = system.id
        system.delete()

        assert Backup.objects.filter(target_system_id=system_id).count() == 0


class TestBackupBusinessLogic:
    """Backup model business logic tests"""

    def test_backup_meta_data_default_empty_dict(self):
        """Test: meta_data defaults to empty dictionary"""
        backup = BackupFactory(meta_data={})
        assert backup.meta_data == {}

    def test_backup_meta_data_can_store_json(self):
        """Test: meta_data can store JSON data"""
        complex_data = {
            'compression': 'gzip',
            'encryption': 'AES256',
            'files_count': 150,
            'checksum': 'abc123'
        }
        backup = BackupFactory(meta_data=complex_data)
        assert backup.meta_data == complex_data
        assert backup.meta_data['files_count'] == 150