"""
Shared fixtures for all tests.
Contains test environment settings, clients, and data factories.
"""
import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.test import override_settings
from datetime import datetime, timedelta
from decimal import Decimal
from django.utils import timezone

from core.models import TargetSystem, Host, Backup

User = get_user_model()


@pytest.fixture
def api_client():
    """Basic API client without authentication"""
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, user):
    """API client with authenticated user"""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def user(db):
    """Regular user for tests"""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def target_system(db):
    """Creates a test system"""
    return TargetSystem.objects.create(
        name='Test System',
        system_type='Linux',
        api_key='550e8400-e29b-41d4-a716-446655440000'
    )


@pytest.fixture
def host(db, target_system):
    """Creates a test host"""
    return Host.objects.create(
        hostname='test-server',
        ip_address='192.168.1.100',
        target_system=target_system
    )


@pytest.fixture
def backup(db, host, target_system):
    """Creates a test backup in in_progress status"""
    return Backup.objects.create(
        host=host,
        target_system=target_system,
        status='in_progress',
        start_time=timezone.now() - timedelta(hours=1),
        storage='/backups/test/'
    )


@pytest.fixture
def completed_backup(db, host, target_system):
    """Creates a completed backup"""
    return Backup.objects.create(
        host=host,
        target_system=target_system,
        status='success',
        start_time=timezone.now() - timedelta(hours=2),
        end_time=timezone.now() - timedelta(hours=1),
        backup_size=1024 * 1024 * 100,  # 100 MB
        storage='/backups/test/',
        meta_data={'compression': 'gzip'}
    )


@pytest.fixture
def sample_target_system_data():
    """Data for creating a system"""
    return {
        'name': 'New System',
        'system_type': 'Windows'
    }


@pytest.fixture
def sample_host_data(target_system):
    """Data for creating a host"""
    return {
        'hostname': 'new-server',
        'ip_address': '10.0.0.50',
        'target_system': target_system.id
    }


@pytest.fixture
def sample_backup_create_data(host, target_system):
    """Data for creating a backup via API"""
    return {
        'host_id': host.id,
        'target_system_id': target_system.id,
        'storage': '/backups/new/'
    }


@pytest.fixture
def sample_backup_update_data():
    """Data for updating a backup"""
    return {
        'status': 'success',
        'backup_size': 2048,
        'meta_data': {'test': True}
    }


@pytest.fixture(autouse=True)
def use_test_db(db):
    """Automatically use test database"""
    pass


@pytest.fixture
def override_settings_for_tests():
    """Override settings for tests"""
    with override_settings(
        DEBUG=True,
        REST_FRAMEWORK={
            'DEFAULT_PERMISSION_CLASSES': [
                'rest_framework.permissions.AllowAny',
            ],
        }
    ):
        yield