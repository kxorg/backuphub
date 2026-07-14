# app/configurations/tests.py
import pytest
from .models import BackupConfiguration, BackupConfigurationVersion
from api.v1.backup_operations.tests.factories import (
    BackupConfigurationFactory,
    BackupConfigurationVersionFactory,
)

pytestmark = pytest.mark.django_db


class TestBackupConfiguration:
    def test_current_version_property(self):
        cfg = BackupConfigurationFactory()
        v1 = BackupConfigurationVersionFactory(
            backup_configuration=cfg, version_number=1, is_current=True
        )
        BackupConfigurationVersionFactory(
            backup_configuration=cfg, version_number=2, is_current=False
        )
        assert cfg.current_version == v1

    def test_str_includes_target_system_name(self):
        cfg = BackupConfigurationFactory(
            name='daily',
            target_system_version__target_system__name='db-01',
        )
        assert 'daily' in str(cfg)
        assert 'db-01' in str(cfg)


class TestBackupConfigurationVersion:
    def test_default_values(self):
        v = BackupConfigurationVersionFactory()
        assert v.backup_mode == 'full'
        assert v.storage_type == 'local'
        assert v.retention_days == 30
        assert v.rpo_minutes == 1440
        assert v.rto_minutes == 60

    def test_unique_together(self):
        from django.db import IntegrityError
        cfg = BackupConfigurationFactory()
        BackupConfigurationVersionFactory(backup_configuration=cfg, version_number=1)
        with pytest.raises(IntegrityError):
            BackupConfigurationVersionFactory(backup_configuration=cfg, version_number=1)