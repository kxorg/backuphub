# app/api/tests/test_ownership.py
import pytest
from django.urls import reverse
from api.v1.backup_operations.tests.factories import (
    BackupConfigurationVersionFactory,
    BackupOperationFactory,
)

pytestmark = pytest.mark.django_db


class TestOwnershipIsolation:
    def test_list_returns_only_own_operations(self, api_client):
        cv_a = BackupConfigurationVersionFactory()
        cv_b = BackupConfigurationVersionFactory()
        
        system_a = cv_a.backup_configuration.target_system_version.target_system
        system_b = cv_b.backup_configuration.target_system_version.target_system

        op_a1 = BackupOperationFactory(backup_configuration_version=cv_a, status='success')
        op_a2 = BackupOperationFactory(backup_configuration_version=cv_a, status='success')
        op_b1 = BackupOperationFactory(backup_configuration_version=cv_b, status='success')

        api_client.logout() 
        api_client.credentials(HTTP_X_API_KEY=str(system_a.api_key))
        
        resp = api_client.get(reverse('backup-operation-list'))
        
        assert resp.status_code == 200
        
        assert resp.data['count'] == 2
        
        returned_ids = [item['id'] for item in resp.data['results']]
        assert op_a1.id in returned_ids
        assert op_a2.id in returned_ids
        assert op_b1.id not in returned_ids  

    def test_cannot_update_foreign_operation(self, api_client):
        cv_a = BackupConfigurationVersionFactory()
        cv_b = BackupConfigurationVersionFactory()
        system_a = cv_a.backup_configuration.target_system_version.target_system

        foreign_op = BackupOperationFactory(
            backup_configuration_version=cv_b, status='in_progress'
        )

        api_client.logout()
        api_client.credentials(HTTP_X_API_KEY=str(system_a.api_key))
        
        url = reverse('backup-operation-detail', args=[foreign_op.id])
        resp = api_client.patch(url, {'status': 'SUCCESS'}, format='json')
        
        assert resp.status_code in [403, 404]