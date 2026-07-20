# app/api/tests/test_authentication.py
import pytest
from django.urls import reverse
from api.v1.backup_operations.tests.factories import (
    BackupConfigurationVersionFactory,
    BackupOperationFactory,
)

pytestmark = pytest.mark.django_db


class TestApiKeyAuthentication:
    @pytest.fixture
    def config_version(self):
        return BackupConfigurationVersionFactory()

    def test_missing_api_key_on_write_returns_401(self, api_client, config_version):
        url = reverse('backup-operation-list')
        api_client.credentials() 
        resp = api_client.post(url, {
            'backup_configuration_id': config_version.backup_configuration_id,
        }, format='json')
        assert resp.status_code in [401, 403]

    def test_invalid_api_key_returns_401(self, api_client, config_version):
        api_client.credentials(HTTP_X_API_KEY='00000000-0000-0000-0000-000000000000')
        url = reverse('backup-operation-list')
        resp = api_client.post(url, {
            'backup_configuration_id': config_version.backup_configuration_id,
        }, format='json')
        assert resp.status_code in [401, 403]

    def test_inactive_system_api_key_returns_401(self, api_client, config_version):
        system = config_version.backup_configuration.target_system_version.target_system
        system.is_active = False
        system.save()
        api_client.credentials(HTTP_X_API_KEY=str(system.api_key))
        url = reverse('backup-operation-list')
        resp = api_client.post(url, {
            'backup_configuration_id': config_version.backup_configuration_id,
        }, format='json')
        assert resp.status_code in [401, 403]

    def test_read_without_api_key_allowed(self, api_client, config_version):
        BackupOperationFactory(
            backup_configuration_version=config_version,
            status='success',
        )
        url = reverse('backup-operation-list')
        resp = api_client.get(url)
        # read allowed by HasValidApiKey, but after ownership fix it returns 0
        assert resp.status_code == 200