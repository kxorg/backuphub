# app/systems/tests.py
import pytest
from .models import TargetSystem, TargetSystemVersion
from dictionaries.models import SystemType, Environment
from api.v1.backup_operations.tests.factories import (
    TargetSystemFactory,
    TargetSystemVersionFactory,
)

pytestmark = pytest.mark.django_db


class TestTargetSystem:
    def test_api_key_generated_on_create(self):
        ts = TargetSystemFactory()
        assert ts.api_key is not None
        assert str(ts.api_key)  # UUID валидный

    def test_api_key_unique(self):
        a = TargetSystemFactory()
        b = TargetSystemFactory()
        assert a.api_key != b.api_key

    def test_current_version_returns_is_current_true(self):
        ts = TargetSystemFactory()
        v1 = TargetSystemVersionFactory(target_system=ts, version_number=1, is_current=True)
        TargetSystemVersionFactory(target_system=ts, version_number=2, is_current=False)
        assert ts.current_version == v1

    def test_current_version_none_when_no_versions(self):
        from systems.models import TargetSystem
        from dictionaries.models import SystemType, Environment
        st = SystemType.objects.create(name='t')
        env = Environment.objects.create(name='e')
        ts = TargetSystem.objects.create(
            system_type=st, environment=env, name='x', is_active=True
        )
        assert ts.current_version is None

    def test_str_returns_name(self):
        ts = TargetSystemFactory(name='prod-db-01')
        assert str(ts) == 'prod-db-01'


class TestTargetSystemVersion:
    def test_unique_together_target_and_version(self):
        from django.db import IntegrityError
        ts = TargetSystemFactory()
        TargetSystemVersionFactory(target_system=ts, version_number=1)
        with pytest.raises(IntegrityError):
            TargetSystemVersionFactory(target_system=ts, version_number=1)

    def test_str_format(self):
        v = TargetSystemVersionFactory(
            target_system__name='db-01', version_number=3
        )
        assert str(v) == 'db-01 v3'