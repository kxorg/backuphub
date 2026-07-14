import pytest
from django.urls import reverse
from .factories import BackupOperationFactory


pytestmark = pytest.mark.django_db


@pytest.fixture
def operation_with_client(api_client):
    op = BackupOperationFactory(status='in_progress')
    system = op.backup_configuration_version.backup_configuration.target_system_version.target_system
    api_client.credentials(HTTP_X_API_KEY=str(system.api_key))
    return api_client, op


class TestUpdateOperation:
    def _url(self, op_id):
        return reverse('backup-operation-detail', args=[op_id])

    def test_complete_with_success(self, operation_with_client):
        client, op = operation_with_client
        resp = client.patch(self._url(op.id), {
            'status': 'SUCCESS',
            'size_bytes': 1024,
            'storage_type': 's3',
            'storage_path': 's3://bucket/backup.sql',
        }, format='json')
        assert resp.status_code == 200
        assert resp.data['status'] == 'SUCCESS'
        op.refresh_from_db()
        assert op.status == 'success'
        assert op.finished_at is not None

    def test_complete_with_failed_requires_error_message(self, operation_with_client):
        client, op = operation_with_client
        resp = client.patch(self._url(op.id), {'status': 'FAILED'}, format='json')
        assert resp.status_code == 400
        assert 'error_message' in resp.data['error']['details']

    def test_cannot_modify_completed_operation(self, operation_with_client):
        client, op = operation_with_client
        op.status = 'success'
        op.save()
        resp = client.patch(self._url(op.id), {'status': 'FAILED'}, format='json')
        assert resp.status_code == 400