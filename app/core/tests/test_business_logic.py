"""
Tests for application business logic.
Testing complex scenarios and integration between components.
"""
import pytest
from django.utils import timezone
from datetime import timedelta

from core.models import Backup, Host, TargetSystem
from .factories import TargetSystemFactory, HostFactory, BackupFactory


pytestmark = pytest.mark.django_db


class TestBackupLifecycle:
    """Backup lifecycle tests"""

    def test_backup_creation_workflow(self):
        """Test: Full backup creation workflow"""
        # 1. Create a host
        host = HostFactory()
        initial_backup_count = Backup.objects.count()

        # 2. Create a backup (simulating creation via API)
        backup = Backup.objects.create(
            host=host,
            target_system=host.target_system,
            status='in_progress',
            start_time=timezone.now(),
            storage='/backups/test/'
        )

        # 3. Verify the backup was created
        assert Backup.objects.count() == initial_backup_count + 1
        assert backup.status == 'in_progress'
        assert backup.start_time is not None
        assert backup.end_time is None
        assert backup.backup_size is None

        # 4. Simulate backup completion (update via API)
        backup.status = 'success'
        backup.end_time = timezone.now()
        backup.backup_size = 1024 * 1024 * 100  # 100 MB
        backup.meta_data = {'compression': 'gzip'}
        backup.save()

        # 5. Verify the backup completed correctly
        backup.refresh_from_db()
        assert backup.status == 'success'
        assert backup.end_time is not None
        assert backup.backup_size == 1024 * 1024 * 100
        assert backup.meta_data['compression'] == 'gzip'
        assert backup.duration is not None

    def test_backup_error_handling(self):
        """Test: Backup error handling"""
        host = HostFactory()

        # Create a backup with error
        backup = Backup.objects.create(
            host=host,
            target_system=host.target_system,
            status='error',
            start_time=timezone.now(),
            end_time=timezone.now(),
            error_message='Connection timeout',
            backup_size=0
        )

        assert backup.status == 'error'
        assert backup.error_message == 'Connection timeout'
        assert backup.backup_size == 0

    def test_backup_end_time_must_be_set_explicitly(self):
        """Test: end_time must be set explicitly when completing a backup"""
        backup = BackupFactory(status='in_progress', end_time=None)

        # Change status to final
        backup.status = 'success'
        backup.save()

        # Verify that end_time was NOT set automatically
        # (this logic should be in the API or explicitly in code)
        assert backup.end_time is None

        # Explicitly set end_time (as done in the API)
        backup.end_time = timezone.now()
        backup.save()

        # Verify that end_time is now set
        backup.refresh_from_db()
        assert backup.end_time is not None


class TestDataRelationships:
    """Data relationship tests"""

    def test_system_hosts_relationship(self):
        """Test: System -> hosts relationship"""
        system = TargetSystemFactory()
        hosts = HostFactory.create_batch(5, target_system=system)

        # Verify reverse relationship
        assert system.hosts.count() == 5
        assert list(system.hosts.all()) == hosts

    def test_host_backups_relationship(self):
        """Test: Host -> backups relationship"""
        host = HostFactory()
        backups = BackupFactory.create_batch(3, host=host)

        assert host.backups.count() == 3
        assert list(host.backups.all()) == backups

    def test_system_backups_relationship(self):
        """Test: System -> backups relationship"""
        system = TargetSystemFactory()
        backups = BackupFactory.create_batch(4, target_system=system)

        assert system.backups.count() == 4
        assert list(system.backups.all()) == backups

    def test_chain_relationship(self):
        """Test: Relationship chain system -> host -> backup"""
        system = TargetSystemFactory()
        host = HostFactory(target_system=system)
        backup = BackupFactory(host=host, target_system=system)

        # Verify all relationships
        assert backup.host == host
        assert backup.target_system == system
        assert host.target_system == system
        assert system.hosts.first() == host
        assert host.backups.first() == backup
        assert system.backups.first() == backup


class TestPerformanceScenarios:
    """Performance and bulk operations tests"""

    def test_bulk_create_backups(self):
        """Test: Bulk backup creation"""
        host = HostFactory()
        count = 50

        backups = []
        for i in range(count):
            backups.append(
                Backup(
                    host=host,
                    target_system=host.target_system,
                    status='success',
                    start_time=timezone.now(),
                    end_time=timezone.now(),
                    backup_size=1024 * (i + 1),
                    storage=f'/backups/bulk/{i}/'
                )
            )

        # Bulk create
        Backup.objects.bulk_create(backups)

        assert Backup.objects.filter(host=host).count() == count

        # Verify that all backups were created with different sizes
        sizes = set(Backup.objects.filter(host=host).values_list('backup_size', flat=True))
        assert len(sizes) == count

    def test_select_related_optimization(self):
        """Test: Query optimization with select_related"""
        # Create data
        host = HostFactory()
        BackupFactory.create_batch(10, host=host)

        from django.db import connection

        # Clear query log
        connection.queries_log.clear()

        # Query with select_related (as in the view)
        backups = Backup.objects.select_related('host', 'target_system').all()

        # Verify data is accessible without additional queries
        for backup in backups:
            assert backup.host is not None
            assert backup.target_system is not None
            # Accessing attributes should not trigger additional queries
            assert backup.host.hostname is not None

        # Check the number of database queries
        # select_related should result in 1 query
        assert len(connection.queries) <= 2  # One query + possibly one for creation