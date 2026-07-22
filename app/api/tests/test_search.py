import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


class TestGlobalSearchAPI:
    """Tests for the global search API /api/search/"""


    # TEST 1: Searching by system name returns the correct TargetSystem.

    def test_search_by_system_name_returns_target_system(self, api_client):
        
        from api.v1.backup_operations.tests.factories import TargetSystemFactory
        
        system = TargetSystemFactory(name='prod-db-01')
        
        resp = api_client.get(reverse('api_global_search'), {'q': 'prod-db'})
        
        assert resp.status_code == 200
        data = resp.json()
        
        assert data['count'] > 0
        
        # We find a result of type target_system.
        system_results = [r for r in data['results'] if r['type'] == 'target_system']
        assert len(system_results) > 0
        
        # We verify that the required system is present in the results.
        system_ids = [r['id'] for r in system_results]
        assert system.id in system_ids
        
        # Checking fields
        found_system = next(r for r in system_results if r['id'] == system.id)
        assert found_system['title'] == 'prod-db-01'
        assert 'PostgreSQL' in found_system['subtitle'] or 'type_' in found_system['subtitle']
        assert found_system['url'] == f'/target-systems/{system.id}/'

 
    # TEST 2: InformationSystem search returns related systems

    def test_search_by_information_system_returns_related_systems(self, api_client):

        from api.v1.backup_operations.tests.factories import (
            TargetSystemFactory,
            InformationSystemFactory,
        )
        
        info_system = InformationSystemFactory(name='CRM System')
        system = TargetSystemFactory(name='crm-db', information_system=info_system)
        
        resp = api_client.get(reverse('api_global_search'), {'q': 'CRM'})
        
        assert resp.status_code == 200
        data = resp.json()
        
        # The information system itself must be found.
        info_results = [r for r in data['results'] if r['type'] == 'information_system']
        assert len(info_results) > 0
        assert info_results[0]['title'] == 'CRM System'
        
        # And the associated Target System
        system_results = [r for r in data['results'] if r['type'] == 'target_system']
        system_names = [r['title'] for r in system_results]
        assert 'crm-db' in system_names


    # TEST 3: Hostname search finds BackupOperation

    def test_search_by_hostname_finds_backup_operation(self, api_client):

        from api.v1.backup_operations.tests.factories import BackupOperationFactory
        
        operation = BackupOperationFactory(hostname='prod-db-01.local')
        
        resp = api_client.get(reverse('api_global_search'), {'q': 'prod-db-01.local'})
        
        assert resp.status_code == 200
        data = resp.json()
        
        operation_results = [r for r in data['results'] if r['type'] == 'backup_operation']
        assert len(operation_results) > 0
        
        found_op = operation_results[0]
        assert found_op['id'] == operation.id
        assert 'prod-db-01.local' in found_op['title']
        assert found_op['url'] == f'/backup-operations/{operation.id}/'


    # TEST 4: An empty query returns the first page of results.

    def test_empty_query_returns_first_page(self, api_client):

        from api.v1.backup_operations.tests.factories import TargetSystemFactory
        
        TargetSystemFactory(name='test-system-1')
        TargetSystemFactory(name='test-system-2')
        
        resp = api_client.get(reverse('api_global_search'), {'q': '', 'page': 1, 'page_size': 25})
        
        assert resp.status_code == 200
        data = resp.json()
        
        assert data['page'] == 1
        assert data['page_size'] == 25
        assert isinstance(data['results'], list)
        assert data['count'] > 0


    # TEST 5: Non-existent request returns an empty list

    def test_nonexistent_query_returns_empty_list(self, api_client):

        resp = api_client.get(reverse('api_global_search'), {'q': 'xyznonexistent999'})
        
        assert resp.status_code == 200
        data = resp.json()
        
        assert data['count'] == 0
        assert data['results'] == []
        assert data['has_next'] is False


    # TEST 6: Pagination check (page, page_size)

    def test_pagination_works_correctly(self, api_client):

        from api.v1.backup_operations.tests.factories import TargetSystemFactory
        
        # We are creating multiple systems to test pagination.
        for i in range(15):
            TargetSystemFactory(name=f'test-system-{i:02d}')
        
        # Page 1, size 5
        resp = api_client.get(reverse('api_global_search'), {'q': 'test-system', 'page': 1, 'page_size': 5})
        data = resp.json()
        
        assert resp.status_code == 200
        assert data['page'] == 1
        assert data['page_size'] == 5
        assert len(data['results']) == 5
        assert data['has_next'] is True
        
        # Page 2
        resp = api_client.get(reverse('api_global_search'), {'q': 'test-system', 'page': 2, 'page_size': 5})
        data = resp.json()
        
        assert resp.status_code == 200
        assert data['page'] == 2
        assert len(data['results']) == 5
        assert data['has_next'] is True
        
        # Page 3 (last)
        resp = api_client.get(reverse('api_global_search'), {'q': 'test-system', 'page': 3, 'page_size': 5})
        data = resp.json()
        
        assert resp.status_code == 200
        assert data['page'] == 3
        assert len(data['results']) == 5
        assert data['has_next'] is False


    # TEST 7: Verification that the response contains the correct fields

    def test_response_contains_correct_fields(self, api_client):

        from api.v1.backup_operations.tests.factories import TargetSystemFactory
        
        TargetSystemFactory(name='test-system')
        
        resp = api_client.get(reverse('api_global_search'), {'q': 'test'})
        
        assert resp.status_code == 200
        data = resp.json()
        
        # Checking the response structure
        assert 'count' in data
        assert 'page' in data
        assert 'page_size' in data
        assert 'has_next' in data
        assert 'results' in data
        
        # We check the structure of each result.
        for result in data['results']:
            assert 'type' in result
            assert 'id' in result
            assert 'title' in result
            assert 'subtitle' in result
            assert 'url' in result
            
            # type must be one of the valid values
            valid_types = [
                'target_system',
                'backup_configuration',
                'backup_operation',
                'backup_tool',
                'system_type',
                'environment',
                'information_system',
            ]
            assert result['type'] in valid_types


    # ADDITIONAL TESTS


    def test_search_requires_authentication(self, api_client):
        """The API requires authorization."""
        # Log out (if api_client is not authorized by default)
        api_client.logout()
        
        resp = api_client.get(reverse('api_global_search'), {'q': 'test'})
        
        # Must return 401 or 403.
        assert resp.status_code in [401, 403]

    def test_search_by_backup_tool_name(self, api_client):
        """Search by backup tool name"""
        from api.v1.backup_operations.tests.factories import BackupToolFactory
        
        tool = BackupToolFactory(name='pg_dump')
        
        resp = api_client.get(reverse('api_global_search'), {'q': 'pg_dump'})
        
        assert resp.status_code == 200
        data = resp.json()
        
        tool_results = [r for r in data['results'] if r['type'] == 'backup_tool']
        assert len(tool_results) > 0
        assert tool_results[0]['title'] == 'pg_dump'

    def test_search_by_system_type_name(self, api_client):
        """Search by system type name"""
        from api.v1.backup_operations.tests.factories import SystemTypeFactory
        
        system_type = SystemTypeFactory(name='PostgreSQL')
        
        resp = api_client.get(reverse('api_global_search'), {'q': 'PostgreSQL'})
        
        assert resp.status_code == 200
        data = resp.json()
        
        type_results = [r for r in data['results'] if r['type'] == 'system_type']
        assert len(type_results) > 0
        assert type_results[0]['title'] == 'PostgreSQL'

    def test_search_by_environment_name(self, api_client):
        """Search by environment name"""
        from api.v1.backup_operations.tests.factories import EnvironmentFactory
        
        env = EnvironmentFactory(name='Production')
        
        resp = api_client.get(reverse('api_global_search'), {'q': 'Production'})
        
        assert resp.status_code == 200
        data = resp.json()
        
        env_results = [r for r in data['results'] if r['type'] == 'environment']
        assert len(env_results) > 0
        assert env_results[0]['title'] == 'Production'

    def test_search_by_backup_configuration_name(self, api_client):
        """Search by "backup configuration" name"""
        from api.v1.backup_operations.tests.factories import BackupConfigurationFactory
        
        config = BackupConfigurationFactory(name='nightly-backup')
        
        resp = api_client.get(reverse('api_global_search'), {'q': 'nightly-backup'})
        
        assert resp.status_code == 200
        data = resp.json()
        
        config_results = [r for r in data['results'] if r['type'] == 'backup_configuration']
        assert len(config_results) > 0
        assert config_results[0]['title'] == 'nightly-backup'

    def test_search_by_external_job_id(self, api_client):
        """Searching by external_job_id finds the operation."""
        from api.v1.backup_operations.tests.factories import BackupOperationFactory
        
        operation = BackupOperationFactory(external_job_id='job-12345')
        
        resp = api_client.get(reverse('api_global_search'), {'q': 'job-12345'})
        
        assert resp.status_code == 200
        data = resp.json()
        
        operation_results = [r for r in data['results'] if r['type'] == 'backup_operation']
        assert len(operation_results) > 0

    def test_page_size_capped_at_100(self, api_client):
        """page_size is capped at a maximum of 100."""
        resp = api_client.get(reverse('api_global_search'), {'q': '', 'page': 1, 'page_size': 500})
        
        assert resp.status_code == 200
        data = resp.json()
        
        assert data['page_size'] == 100

    def test_invalid_page_returns_first_page(self, api_client):
        """An invalid page number returns the first page."""
        resp = api_client.get(reverse('api_global_search'), {'q': '', 'page': 'invalid', 'page_size': 25})
        
        assert resp.status_code == 200
        data = resp.json()
        
        assert data['page'] == 1

    def test_search_is_case_insensitive(self, api_client):
        """Case-insensitive search"""
        from api.v1.backup_operations.tests.factories import TargetSystemFactory
        
        TargetSystemFactory(name='prod-db')
        
        resp_lower = api_client.get(reverse('api_global_search'), {'q': 'prod-db'})
        resp_upper = api_client.get(reverse('api_global_search'), {'q': 'PROD-DB'})
        
        assert resp_lower.status_code == 200
        assert resp_upper.status_code == 200
        
        data_lower = resp_lower.json()
        data_upper = resp_upper.json()
        
        # They must return the same number of results.
        assert data_lower['count'] == data_upper['count']