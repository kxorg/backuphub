import pytest
from rest_framework.test import APIClient
from systems.models import TargetSystem
from dictionaries.models import SystemType, Environment, BackupTool


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def system_type(db):
    return SystemType.objects.create(name='PostgreSQL', description='pg')


@pytest.fixture
def environment(db):
    return Environment.objects.create(name='Production')


@pytest.fixture
def backup_tool(db):
    return BackupTool.objects.create(name='pg_dump', is_active=True)


@pytest.fixture
def target_system(db, system_type, environment):
    return TargetSystem.objects.create(
        system_type=system_type,
        environment=environment,
        name='test-db-01',
        is_active=True,
    )