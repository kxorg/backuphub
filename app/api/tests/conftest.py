import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    """Fixture for an authenticated API client"""
    client = APIClient()
    user = User.objects.create_user(
        username='testuser',
        password='testpass123'
    )
    client.force_authenticate(user=user)
    return client