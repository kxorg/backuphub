"""
Tests for API ViewSet (Backup API).
Testing CRUD operations, validation, response statuses.
"""
import pytest
from rest_framework import status
from rest_framework.reverse import reverse
from django.utils import timezone
from datetime import timedelta

from core.models import Backup
from .factories import (
    TargetSystemFactory, HostFactory, BackupFactory, CompletedBackupFactory
)


pytestmark = pytest.mark.django_db


class TestBackupAPI:
    """Tests for Backup API"""

    def test_list_backups_unauthenticated(self, api_client):
        """Test: Unauthenticated user cannot see backups"""
        BackupFactory.create_batch(5)
        url = reverse('backup-list')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_backups_empty(self, authenticated_client):
        """Test: Backup list is empty"""
        url = reverse('backup-list')
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data == []

    def test_retrieve_backup(self, authenticated_client):
        """Test: Retrieve a specific backup"""
        backup = BackupFactory()
        url = reverse('backup-detail', kwargs={'pk': backup.id})
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(backup.id)
        assert response.data['status'] == backup.status

    def test_retrieve_nonexistent_backup(self, authenticated_client):
        """Test: Retrieve a non-existent backup"""
        url = reverse('backup-detail', kwargs={'pk': '00000000-0000-0000-0000-000000000000'})
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_backup_success(self, authenticated_client):
        """Test: Successful backup creation"""
        host = HostFactory()
        data = {
            'host_id': host.id,
            'storage': '/backups/test/'
        }
        url = reverse('backup-list')
        response = authenticated_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['status'] == 'in_progress'
        assert response.data['host'] == host.id
        assert response.data['target_system'] == host.target_system.id
        assert 'start_time' in response.data

        # Verify the backup was created in the database
        backup_id = response.data['id']
        backup = Backup.objects.get(id=backup_id)
        assert backup.status == 'in_progress'
        assert backup.host == host

    def test_create_backup_with_target_system(self, authenticated_client):
        """Test: Creating a backup with specified target system"""
        host = HostFactory()
        system = TargetSystemFactory()
        data = {
            'host_id': host.id,
            'target_system_id': system.id,
            'storage': '/backups/test/'
        }
        url = reverse('backup-list')
        response = authenticated_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['target_system'] == system.id

    def test_create_backup_auto_system_from_host(self, authenticated_client):
        """Test: If target_system_id is not specified, it is taken from the host"""
        system = TargetSystemFactory()
        host = HostFactory(target_system=system)
        data = {
            'host_id': host.id,
            'storage': '/backups/test/'
        }
        url = reverse('backup-list')
        response = authenticated_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['target_system'] == system.id

    def test_create_backup_invalid_host(self, authenticated_client):
        """Test: Creating a backup with non-existent host"""
        data = {
            'host_id': 99999,
            'storage': '/backups/test/'
        }
        url = reverse('backup-list')
        response = authenticated_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'host_id' in response.data

    def test_create_backup_invalid_target_system(self, authenticated_client):
        """Test: Creating a backup with non-existent system"""
        host = HostFactory()
        data = {
            'host_id': host.id,
            'target_system_id': 99999,
            'storage': '/backups/test/'
        }
        url = reverse('backup-list')
        response = authenticated_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'target_system_id' in response.data

    def test_create_backup_missing_host_id(self, authenticated_client):
        """Test: Creating a backup without host_id"""
        data = {
            'storage': '/backups/test/'
        }
        url = reverse('backup-list')
        response = authenticated_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'host_id' in response.data

    def test_update_backup_success(self, authenticated_client):
        """Test: Successful backup update"""
        backup = BackupFactory(status='in_progress', end_time=None)
        data = {
            'status': 'success',
            'backup_size': 1024
        }
        url = reverse('backup-detail', kwargs={'pk': backup.id})
        response = authenticated_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'success'
        assert response.data['backup_size'] == 1024
        assert response.data['end_time'] is not None

        # Verify end_time was set automatically
        backup.refresh_from_db()
        assert backup.end_time is not None

    def test_update_backup_partial(self, authenticated_client):
        """Test: Partial backup update"""
        backup = BackupFactory(
            status='in_progress',
            storage='/old/path/',
            meta_data={'old': 'data'}
        )
        data = {
            'storage': '/new/path/'
        }
        url = reverse('backup-detail', kwargs={'pk': backup.id})
        response = authenticated_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['storage'] == '/new/path/'
        assert response.data['meta_data'] == {'old': 'data'}  # Unchanged

    def test_update_backup_final_status_with_end_time(self, authenticated_client):
        """Test: Setting final status automatically adds end_time"""
        backup = BackupFactory(status='in_progress', end_time=None)
        data = {'status': 'error'}
        url = reverse('backup-detail', kwargs={'pk': backup.id})
        response = authenticated_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'error'
        assert response.data['end_time'] is not None

    def test_update_backup_does_not_override_end_time(self, authenticated_client):
        """Test: If end_time is already set, it is not overwritten"""
        old_end_time = timezone.now() - timedelta(hours=1)
        backup = BackupFactory(
            status='success',
            end_time=old_end_time
        )
        data = {'status': 'error'}  # Change status to error
        url = reverse('backup-detail', kwargs={'pk': backup.id})
        response = authenticated_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'error'
        # end_time should remain the old one
        assert response.data['end_time'] == old_end_time.isoformat().replace('+00:00', 'Z')

    def test_update_backup_invalid_data(self, authenticated_client):
        """Test: Update with invalid data"""
        backup = BackupFactory()
        data = {
            'status': 'invalid_status',
            'backup_size': -100
        }
        url = reverse('backup-detail', kwargs={'pk': backup.id})
        response = authenticated_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'status' in response.data or 'backup_size' in response.data

    def test_update_nonexistent_backup(self, authenticated_client):
        """Test: Update non-existent backup"""
        data = {'status': 'success'}
        url = reverse('backup-detail', kwargs={'pk': '00000000-0000-0000-0000-000000000000'})
        response = authenticated_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_backup_serialization_format(self, authenticated_client):
        """Test: Response format validation"""
        backup = CompletedBackupFactory()
        url = reverse('backup-detail', kwargs={'pk': backup.id})
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.data

        # Verify all fields are present
        assert 'id' in data
        assert 'hostname' in data
        assert 'system_name' in data
        assert 'duration_seconds' in data
        assert 'meta_data' in data

        # Verify types
        assert isinstance(data['duration_seconds'], int)
        assert isinstance(data['meta_data'], dict)

    def test_backup_filtering_not_implemented(self, authenticated_client):
        """Test: Filtering by status (if implemented)"""
        BackupFactory.create_batch(3, status='success')
        BackupFactory.create_batch(2, status='in_progress')

        # Without filtering, return all
        url = reverse('backup-list')
        response = authenticated_client.get(url)
        assert len(response.data) == 5
