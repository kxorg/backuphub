"""
Factories for creating test data.
Used to reduce code duplication in tests.
"""
import factory
from factory.django import DjangoModelFactory
from django.utils import timezone
import uuid
from datetime import timedelta

from core.models import TargetSystem, Host, Backup


class TargetSystemFactory(DjangoModelFactory):
    """Factory for creating target systems"""

    class Meta:
        model = TargetSystem

    name = factory.Sequence(lambda n: f'System {n}')
    system_type = factory.Iterator(['Linux', 'Windows', 'MacOS'])
    api_key = factory.LazyFunction(uuid.uuid4)
    created_at = factory.LazyFunction(timezone.now)


class HostFactory(DjangoModelFactory):
    """Factory for creating hosts"""

    class Meta:
        model = Host

    hostname = factory.Sequence(lambda n: f'server-{n:03d}')
    ip_address = factory.Sequence(lambda n: f'192.168.1.{n+1}')
    target_system = factory.SubFactory(TargetSystemFactory)


class BackupFactory(DjangoModelFactory):
    """Factory for creating backups"""

    class Meta:
        model = Backup

    id = factory.LazyFunction(uuid.uuid4)
    host = factory.SubFactory(HostFactory)
    target_system = factory.SelfAttribute('host.target_system')
    status = factory.Iterator(['in_progress', 'success', 'error'])
    start_time = factory.LazyFunction(timezone.now)
    end_time = None
    backup_size = None
    storage = factory.Sequence(lambda n: f'/backups/storage-{n:03d}')
    meta_data = factory.LazyFunction(lambda: {})
    error_message = None


class CompletedBackupFactory(BackupFactory):
    """Factory for creating completed backups"""

    status = 'success'
    end_time = factory.LazyFunction(
        lambda: timezone.now() - timedelta(hours=1)
    )
    backup_size = factory.Sequence(lambda n: 1024 * 1024 * (n + 1))  # MB