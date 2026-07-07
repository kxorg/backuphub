"""
Tests for Web Views (HTML templates).
Testing page rendering and CRUD operations via forms.
"""
import pytest
from django.urls import reverse
from django.test import Client
from django.utils import timezone
from django.core.paginator import Paginator

from core.models import TargetSystem, Host, Backup
from .factories import TargetSystemFactory, HostFactory, BackupFactory


pytestmark = pytest.mark.django_db


class TestWebViews:
    """Tests for Web Views"""

    @pytest.fixture
    def client(self, user):
        """Authenticated test client for web requests"""
        client = Client()
        client.force_login(user)
        return client

    # === Main pages ===

    def test_index_page(self, client):
        """Test: Main page"""
        response = client.get(reverse('index'))
        assert response.status_code == 200
        # Verify content contains HTML
        content = response.content.decode()
        assert 'html' in content.lower() or 'DOCTYPE' in content.upper()

    def test_api_page(self, client):
        """Test: API documentation page"""
        response = client.get(reverse('api'))
        assert response.status_code == 200
        # Verify content contains HTML
        content = response.content.decode()
        assert 'html' in content.lower() or 'DOCTYPE' in content.upper()

    # === Backup Views ===

    def test_backup_list(self, client):
        """Test: Backup list with pagination"""
        BackupFactory.create_batch(15)  # Create 15 backups
        response = client.get(reverse('backup_list'))

        assert response.status_code == 200
        assert 'page_obj' in response.context

        # Verify pagination (10 per page)
        page_obj = response.context['page_obj']
        assert len(page_obj) == 10  # First page
        assert page_obj.number == 1
        assert page_obj.has_next() is True

    def test_backup_list_pagination_page_2(self, client):
        """Test: Pagination - second page"""
        BackupFactory.create_batch(15)
        response = client.get(reverse('backup_list') + '?page=2')

        assert response.status_code == 200
        page_obj = response.context['page_obj']
        assert len(page_obj) == 5  # Second page
        assert page_obj.number == 2

    def test_backup_list_ordered_by_start_time(self, client):
        """Test: Backup list ordered by creation time"""
        backup1 = BackupFactory(start_time=timezone.now() - timezone.timedelta(hours=2))
        backup2 = BackupFactory(start_time=timezone.now() - timezone.timedelta(hours=1))
        backup3 = BackupFactory(start_time=timezone.now())

        response = client.get(reverse('backup_list'))
        backups = response.context['page_obj']

        # Verify newest first
        assert backups[0].start_time > backups[1].start_time
        assert backups[1].start_time > backups[2].start_time

    def test_backup_detail(self, client):
        """Test: Backup detail page"""
        backup = BackupFactory()
        response = client.get(reverse('backup_detail', args=[backup.id]))

        assert response.status_code == 200
        assert response.context['backup'] == backup

    def test_backup_detail_not_found(self, client):
        """Test: Detail page for non-existent backup"""
        response = client.get(reverse('backup_detail', args=['00000000-0000-0000-0000-000000000000']))
        assert response.status_code == 404

    # === TargetSystem CRUD ===

    def test_system_list(self, client):
        """Test: System list"""
        TargetSystemFactory.create_batch(7)
        response = client.get(reverse('target_system_list'))

        assert response.status_code == 200
        page_obj = response.context['page_obj']
        assert len(page_obj) == 5  # Pagination: 5 per page

    def test_system_create_get(self, client):
        """Test: System creation form (GET)"""
        response = client.get(reverse('target_system_create'))
        assert response.status_code == 200

    def test_system_create_post_success(self, client):
        """Test: System creation (POST)"""
        data = {
            'name': 'New System',
            'system_type': 'Linux'
        }
        response = client.post(reverse('target_system_create'), data)

        assert response.status_code == 302  # Redirect
        assert response.url == reverse('target_system_list')

        # Verify the system was created
        assert TargetSystem.objects.filter(name='New System').exists()
        system = TargetSystem.objects.get(name='New System')
        assert system.system_type == 'Linux'
        assert system.api_key is not None

    def test_system_create_post_missing_name(self, client):
        """Test: Creating a system without name returns an error"""
        data = {
            'system_type': 'Linux'
        }
        response = client.post(reverse('target_system_create'), data)

        # Verify the same page was returned with an error
        assert response.status_code == 200
        assert 'error' in response.context or b'error' in response.content.lower()
        # Verify the system was not created
        assert TargetSystem.objects.count() == 0

    def test_system_edit_get(self, client):
        """Test: System edit form (GET)"""
        system = TargetSystemFactory()
        response = client.get(reverse('target_system_edit', args=[system.id]))

        assert response.status_code == 200
        assert response.context['system'] == system

    def test_system_edit_post_success(self, client):
        """Test: System edit (POST)"""
        system = TargetSystemFactory(name='Old Name', system_type='Windows')
        data = {
            'name': 'Updated Name',
            'system_type': 'Linux'
        }
        response = client.post(reverse('target_system_edit', args=[system.id]), data)

        assert response.status_code == 302
        assert response.url == reverse('target_system_list')

        # Verify data was updated
        system.refresh_from_db()
        assert system.name == 'Updated Name'
        assert system.system_type == 'Linux'

    def test_system_delete_get(self, client):
        """Test: Delete confirmation page (GET)"""
        system = TargetSystemFactory()
        response = client.get(reverse('target_system_delete', args=[system.id]))

        assert response.status_code == 200
        assert response.context['system'] == system

    def test_system_delete_post_success(self, client):
        """Test: System deletion (POST)"""
        system = TargetSystemFactory()
        system_id = system.id

        response = client.post(reverse('target_system_delete', args=[system_id]))

        assert response.status_code == 302
        assert response.url == reverse('target_system_list')
        assert not TargetSystem.objects.filter(id=system_id).exists()

    def test_system_delete_with_hosts(self, client):
        """Test: Deleting a system with hosts (cascade delete)"""
        system = TargetSystemFactory()
        HostFactory.create_batch(3, target_system=system)

        response = client.post(reverse('target_system_delete', args=[system.id]))

        assert response.status_code == 302
        assert not TargetSystem.objects.filter(id=system.id).exists()
        assert Host.objects.filter(target_system=system).count() == 0

    # === Host CRUD ===

    def test_host_list(self, client):
        """Test: Host list"""
        HostFactory.create_batch(8)
        response = client.get(reverse('host_list'))

        assert response.status_code == 200
        page_obj = response.context['page_obj']
        assert len(page_obj) == 5  # Pagination: 5 per page

    def test_host_create_get(self, client):
        """Test: Host creation form (GET)"""
        response = client.get(reverse('host_create'))
        assert response.status_code == 200
        assert 'systems' in response.context

    def test_host_create_post_success(self, client):
        """Test: Host creation (POST)"""
        system = TargetSystemFactory()
        data = {
            'hostname': 'web-server',
            'ip_address': '192.168.1.10',
            'target_system': system.id
        }
        response = client.post(reverse('host_create'), data)

        assert response.status_code == 302
        assert response.url == reverse('host_list')

        # Verify the host was created
        assert Host.objects.filter(hostname='web-server').exists()
        host = Host.objects.get(hostname='web-server')
        assert host.ip_address == '192.168.1.10'
        assert host.target_system == system

    def test_host_create_post_invalid_system(self, client):
        """Test: Creating a host with non-existent system"""
        data = {
            'hostname': 'web-server',
            'ip_address': '192.168.1.10',
            'target_system': 99999
        }
        response = client.post(reverse('host_create'), data)

        assert response.status_code == 404  # get_object_or_404 raises 404

    def test_host_edit_get(self, client):
        """Test: Host edit form (GET)"""
        host = HostFactory()
        response = client.get(reverse('host_edit', args=[host.id]))

        assert response.status_code == 200
        assert response.context['host'] == host
        assert 'systems' in response.context

    def test_host_edit_post_success(self, client):
        """Test: Host edit (POST)"""
        host = HostFactory(hostname='old-server', ip_address='10.0.0.1')
        new_system = TargetSystemFactory()

        data = {
            'hostname': 'new-server',
            'ip_address': '10.0.0.2',
            'target_system': new_system.id
        }
        response = client.post(reverse('host_edit', args=[host.id]), data)

        assert response.status_code == 302
        assert response.url == reverse('host_list')

        host.refresh_from_db()
        assert host.hostname == 'new-server'
        assert host.ip_address == '10.0.0.2'
        assert host.target_system == new_system

    def test_host_delete_get(self, client):
        """Test: Host delete confirmation page (GET)"""
        host = HostFactory()
        response = client.get(reverse('host_delete', args=[host.id]))

        assert response.status_code == 200
        assert response.context['host'] == host

    def test_host_delete_post_success(self, client):
        """Test: Host deletion (POST)"""
        host = HostFactory()
        host_id = host.id

        response = client.post(reverse('host_delete', args=[host_id]))

        assert response.status_code == 302
        assert response.url == reverse('host_list')
        assert not Host.objects.filter(id=host_id).exists()

    def test_host_delete_with_backups(self, client):
        """Test: Deleting a host with backups (host becomes NULL)"""
        host = HostFactory()
        backup = BackupFactory(host=host)

        response = client.post(reverse('host_delete', args=[host.id]))

        assert response.status_code == 302
        assert not Host.objects.filter(id=host.id).exists()

        # Backup should remain, but host = NULL
        backup.refresh_from_db()
        assert backup.host is None

    # === Integration tests ===

    def test_full_workflow_create_system_host_backup(self, client):
        """Test: Full workflow - create system, host, and backup"""
        # 1. Create a system
        system_data = {'name': 'Prod', 'system_type': 'Linux'}
        client.post(reverse('target_system_create'), system_data)
        system = TargetSystem.objects.get(name='Prod')

        # 2. Create a host
        host_data = {
            'hostname': 'prod-server',
            'ip_address': '192.168.1.100',
            'target_system': system.id
        }
        client.post(reverse('host_create'), host_data)
        host = Host.objects.get(hostname='prod-server')

        # 3. Create a backup (via API or directly)
        backup = Backup.objects.create(
            host=host,
            target_system=system,
            status='in_progress',
            start_time=timezone.now(),
            storage='/backups/prod/'
        )

        # 4. Verify everything was created
        assert TargetSystem.objects.count() == 1
        assert Host.objects.count() == 1
        assert Backup.objects.count() == 1

        # 5. Verify relationships
        assert host.target_system == system
        assert backup.host == host
        assert backup.target_system == system

    def test_pagination_in_all_lists(self, client):
        """Test: Pagination works in all lists"""
        # Test pagination for systems
        TargetSystemFactory.create_batch(12)
        response = client.get(reverse('target_system_list'))
        assert len(response.context['page_obj']) == 5

        # Test pagination for hosts
        HostFactory.create_batch(12)
        response = client.get(reverse('host_list'))
        assert len(response.context['page_obj']) == 5

        # Test pagination for backups
        BackupFactory.create_batch(12)
        response = client.get(reverse('backup_list'))
        assert len(response.context['page_obj']) == 10
