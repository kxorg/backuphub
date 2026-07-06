"""
Tests for core application serializers.
Testing serialization, deserialization, and data validation.
"""
import pytest
from rest_framework import serializers
from datetime import timedelta
from django.utils import timezone

from core.models import TargetSystem, Host, Backup
from core.serializers import (
    TargetSystemSerializer, HostSerializer, BackupSerializer,
    BackupCreateSerializer, BackupUpdateSerializer
)
from .factories import (
    TargetSystemFactory, HostFactory, BackupFactory, CompletedBackupFactory
)


pytestmark = pytest.mark.django_db


class TestTargetSystemSerializer:
    """Tests for TargetSystemSerializer"""

    def test_serializer_contains_expected_fields(self):
        """Test: Serializer contains expected fields"""
        system = TargetSystemFactory()
        serializer = TargetSystemSerializer(system)
        data = serializer.data

        expected_fields = {'id', 'name', 'system_type', 'api_key', 'created_at'}
        assert set(data.keys()) == expected_fields

    def test_serializer_api_key_read_only(self):
        """Test: API key should not be editable"""
        system = TargetSystemFactory(api_key='550e8400-e29b-41d4-a716-446655440000')
        serializer = TargetSystemSerializer(system)
        data = serializer.data

        # Verify api_key is read-only
        assert 'api_key' in data
        assert data['api_key'] == str(system.api_key)

    def test_serializer_create_valid_data(self):
        """Test: Creating a system via serializer"""
        data = {
            'name': 'Test System',
            'system_type': 'Linux'
        }
        serializer = TargetSystemSerializer(data=data)
        assert serializer.is_valid()
        system = serializer.save()

        assert system.name == 'Test System'
        assert system.system_type == 'Linux'
        assert system.api_key is not None  # Auto-generated

    def test_serializer_create_invalid_data(self):
        """Test: Validation on creation"""
        data = {
            'name': '',  # Empty name
            'system_type': 'Windows'
        }
        serializer = TargetSystemSerializer(data=data)
        assert not serializer.is_valid()
        assert 'name' in serializer.errors


class TestHostSerializer:
    """Tests for HostSerializer"""

    def test_serializer_contains_expected_fields(self):
        """Test: Serializer contains expected fields"""
        host = HostFactory()
        serializer = HostSerializer(host)
        data = serializer.data

        expected_fields = {
            'id', 'hostname', 'ip_address', 'target_system', 'system_name'
        }
        assert set(data.keys()) == expected_fields

    def test_serializer_system_name_read_only(self):
        """Test: system_name is a read-only field"""
        system = TargetSystemFactory(name='Production')
        host = HostFactory(target_system=system)
        serializer = HostSerializer(host)
        data = serializer.data

        assert data['system_name'] == 'Production'

        # Attempt to update system_name (should be ignored)
        update_data = {'system_name': 'New Name'}
        serializer = HostSerializer(host, data=update_data, partial=True)
        assert serializer.is_valid()
        updated_host = serializer.save()

        # Name should not change
        assert updated_host.target_system.name == 'Production'

    def test_serializer_create_with_target_system(self):
        """Test: Creating a host with a specified system"""
        system = TargetSystemFactory()
        data = {
            'hostname': 'web-server',
            'ip_address': '10.0.0.10',
            'target_system': system.id
        }
        serializer = HostSerializer(data=data)
        assert serializer.is_valid()
        host = serializer.save()

        assert host.hostname == 'web-server'
        assert host.target_system == system


class TestBackupSerializer:
    """Tests for BackupSerializer"""

    def test_serializer_contains_expected_fields(self):
        """Test: Serializer contains expected fields"""
        backup = BackupFactory()
        serializer = BackupSerializer(backup)
        data = serializer.data

        expected_fields = {
            'id', 'host', 'target_system', 'hostname', 'system_name',
            'status', 'start_time', 'end_time', 'duration_seconds',
            'backup_size', 'storage', 'meta_data', 'error_message'
        }
        assert set(data.keys()) == expected_fields

    def test_serializer_read_only_fields(self):
        """Test: ID and start_time are read-only"""
        backup = BackupFactory(start_time=timezone.now())
        serializer = BackupSerializer(backup)
        data = serializer.data

        assert 'id' in data
        assert 'start_time' in data
        assert isinstance(data['start_time'], str)

    def test_serializer_duration_calculation(self):
        """Test: Duration calculation in seconds"""
        now = timezone.now()

        backup = BackupFactory(
            status='success',
            start_time=now - timedelta(hours=2),
            end_time=now
        )

        serializer = BackupSerializer(backup)
        data = serializer.data

        assert data['duration_seconds'] is not None
        assert isinstance(data['duration_seconds'], int)
        assert data['duration_seconds'] > 0
        # Verify duration is approximately 2 hours (7200 seconds)
        # Allow a margin of 10 seconds due to microseconds
        assert abs(data['duration_seconds'] - 7200) < 10

    def test_serializer_duration_none_for_incomplete(self):
        """Test: Duration is None for incomplete backup"""
        backup = BackupFactory(status='in_progress', end_time=None)
        serializer = BackupSerializer(backup)
        data = serializer.data

        assert data['duration_seconds'] is None

    def test_serializer_hostname_and_system_name(self):
        """Test: Hostname and system name substitution"""
        system = TargetSystemFactory(name='Production')
        host = HostFactory(hostname='db01', target_system=system)
        backup = BackupFactory(host=host, target_system=system)

        serializer = BackupSerializer(backup)
        data = serializer.data

        assert data['hostname'] == 'db01'
        assert data['system_name'] == 'Production'


class TestBackupCreateSerializer:
    """Tests for BackupCreateSerializer"""

    def test_create_serializer_validation_success(self):
        """Test: Successful validation"""
        host = HostFactory()
        data = {
            'host_id': host.id,
            'storage': '/backups/test/'
        }
        serializer = BackupCreateSerializer(data=data)
        assert serializer.is_valid()
        assert serializer.validated_data['host_id'] == host.id

    def test_create_serializer_validation_with_target_system(self):
        """Test: Validation with specified target system"""
        host = HostFactory()
        system = TargetSystemFactory()
        data = {
            'host_id': host.id,
            'target_system_id': system.id,
            'storage': '/backups/test/'
        }
        serializer = BackupCreateSerializer(data=data)
        assert serializer.is_valid()
        assert serializer.validated_data['target_system_id'] == system.id

    def test_create_serializer_invalid_host_id(self):
        """Test: Non-existent host_id"""
        data = {
            'host_id': 99999,  # Non-existent ID
            'storage': '/backups/test/'
        }
        serializer = BackupCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert 'host_id' in serializer.errors
        assert "not found" in str(serializer.errors['host_id'])

    def test_create_serializer_invalid_target_system_id(self):
        """Test: Non-existent target_system_id"""
        host = HostFactory()
        data = {
            'host_id': host.id,
            'target_system_id': 99999,
            'storage': '/backups/test/'
        }
        serializer = BackupCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert 'target_system_id' in serializer.errors

    def test_create_serializer_missing_required_field(self):
        """Test: Missing required field host_id"""
        data = {
            'storage': '/backups/test/'
        }
        serializer = BackupCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert 'host_id' in serializer.errors


class TestBackupUpdateSerializer:
    """Tests for BackupUpdateSerializer"""

    def test_update_serializer_all_fields_optional(self):
        """Test: All fields are optional"""
        data = {
            'status': 'success'
        }
        serializer = BackupUpdateSerializer(data=data)
        assert serializer.is_valid()
        assert serializer.validated_data['status'] == 'success'

    def test_update_serializer_status_choices(self):
        """Test: Status must be from allowed values"""
        data = {'status': 'invalid_status'}
        serializer = BackupUpdateSerializer(data=data)
        assert not serializer.is_valid()
        assert 'status' in serializer.errors

    def test_update_serializer_backup_size_positive(self):
        """Test: backup_size must be positive"""
        data = {'backup_size': -100}
        serializer = BackupUpdateSerializer(data=data)
        assert not serializer.is_valid()
        assert 'backup_size' in serializer.errors

    def test_update_serializer_json_field(self):
        """Test: meta_data must be JSON"""
        data = {'meta_data': {'key': 'value'}}
        serializer = BackupUpdateSerializer(data=data)
        assert serializer.is_valid()
        assert serializer.validated_data['meta_data'] == {'key': 'value'}

    def test_update_serializer_empty_meta_data(self):
        """Test: meta_data can be empty"""
        data = {'meta_data': {}}
        serializer = BackupUpdateSerializer(data=data)
        assert serializer.is_valid()
        assert serializer.validated_data['meta_data'] == {}