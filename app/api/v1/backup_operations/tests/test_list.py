import pytest
from django.urls import reverse
from .factories import BackupOperationFactory


pytestmark = pytest.mark.django_db


@pytest.fixture
def system_with_operations(api_client):
    op = BackupOperationFactory(status='success')
    system = op.backup_configuration_version.backup_configuration.target_system_version.target_system
    api_client.credentials(HTTP_X_API_KEY=str(system.api_key))
    # создаём ещё 2 операции
    BackupOperationFactory(
        backup_configuration_version=op.backup_configuration_version,
        status='error',
    )
    BackupOperationFactory(
        backup_configuration_version=op.backup_configuration_version,
        status='in_progress',
    )
    return api_client, system


class TestListOperations:
    url = reverse('backup-operation-list')

    def test_list_returns_paginated(self, system_with_operations):
        client, _ = system_with_operations
        resp = client.get(self.url)
        assert resp.status_code == 200
        assert resp.data['count'] == 3
        assert len(resp.data['results']) == 3

    def test_filter_by_status(self, system_with_operations):
        client, _ = system_with_operations
        resp = client.get(self.url, {'status': 'success'})
        assert resp.status_code == 200
        assert resp.data['count'] == 1
        assert resp.data['results'][0]['status'] == 'success'

    def test_filter_by_hostname(self, system_with_operations):
        client, _ = system_with_operations
        resp = client.get(self.url, {'hostname': 'test-host'})
        assert resp.status_code == 200
        assert resp.data['count'] == 3