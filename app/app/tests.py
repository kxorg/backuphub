import pytest
from django.urls import reverse
from django.contrib.auth.models import User

pytestmark = pytest.mark.django_db


class TestDashboardView:
    def test_index_requires_login(self, client):
        resp = client.get(reverse('index'))
        assert resp.status_code == 302
        assert '/login/' in resp.url

    def test_index_returns_200_for_authenticated_user(self, client):
        User.objects.create_user(username='testuser', password='testpass')
        client.login(username='testuser', password='testpass')
        resp = client.get(reverse('index'))
        assert resp.status_code == 200
        assert b'BackupHub' in resp.content


class TestLogoutView:
    def test_logout_redirects_to_login(self, client):
        User.objects.create_user(username='testuser', password='testpass')
        client.login(username='testuser', password='testpass')
        resp = client.get(reverse('logout'))
        assert resp.status_code == 302
        assert '/login/' in resp.url