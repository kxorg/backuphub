import pytest
from django.urls import reverse
from operations.models import BackupOperation


pytestmark = pytest.mark.django_db


@pytest.fixture
def config_version():
    from .factories import BackupConfigurationVersionFactory
    return BackupConfigurationVersionFactory()


@pytest.fixture
def api_client_with_key(api_client, config_version):
    system = config_version.backup_configuration.target_system_version.target_system
    api_client.credentials(HTTP_X_API_KEY=str(system.api_key))
    return api_client, system


class TestCreateOperation:
    url = reverse('backup-operation-list')

    def test_create_success(self, api_client_with_key, config_version):
        client, system = api_client_with_key
        payload = {
            'backup_configuration_id': config_version.backup_configuration_id,
            'hostname': 'srv-01',
            'ip_address': '10.0.0.1',
        }
        resp = client.post(self.url, payload, format='json')
        assert resp.status_code == 201
        assert resp.data['status'] == 'running'
        assert resp.data['hostname'] == 'srv-01'
        assert BackupOperation.objects.filter(id=resp.data['id']).exists()

    def test_create_without_api_key_returns_401(self, api_client, config_version):
        resp = api_client.post(self.url, {
            'backup_configuration_id': config_version.backup_configuration_id,
        }, format='json')
        assert resp.status_code == 401

    def test_create_with_wrong_api_key_returns_403(self, api_client, config_version):
        from systems.models import TargetSystem
        other = TargetSystem.objects.create(
            system_type=config_version.backup_configuration
                .target_system_version.target_system.system_type,
            environment=config_version.backup_configuration
                .target_system_version.target_system.environment,
            name='other',
            is_active=True,
        )
        api_client.credentials(HTTP_X_API_KEY=str(other.api_key))
        resp = api_client.post(self.url, {
            'backup_configuration_id': config_version.backup_configuration_id,
        }, format='json')
        assert resp.status_code == 403

    def test_create_inactive_config_returns_400(self, api_client_with_key, config_version):
        client, _ = api_client_with_key
        config_version.backup_configuration.is_active = False
        config_version.backup_configuration.save()
        resp = client.post(self.url, {
            'backup_configuration_id': config_version.backup_configuration_id,
        }, format='json')
        assert resp.status_code == 400