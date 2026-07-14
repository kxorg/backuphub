# app/operations/tests.py
import pytest
from datetime import timedelta
from django.utils import timezone
from .models import BackupOperation
from api.v1.backup_operations.tests.factories import (
    BackupConfigurationVersionFactory,
    BackupOperationFactory,
)

pytestmark = pytest.mark.django_db


class TestBackupOperationModel:
    def test_duration_seconds_calculation(self):
        op = BackupOperationFactory(status='success')
        op.started_at = timezone.now() - timedelta(minutes=5, seconds=30)
        op.finished_at = timezone.now()
        op.save()
        assert op.duration_seconds == 330

    def test_duration_seconds_none_when_not_finished(self):
        op = BackupOperationFactory(status='in_progress')
        assert op.duration_seconds is None

    def test_size_human_bytes(self):
        op = BackupOperationFactory(size_bytes=500)
        assert op.size_human == '500.0 B'

    def test_size_human_kilobytes(self):
        op = BackupOperationFactory(size_bytes=2048)
        assert op.size_human == '2.0 KB'

    def test_size_human_gigabytes(self):
        op = BackupOperationFactory(size_bytes=5 * 1024 * 1024 * 1024)
        assert op.size_human == '5.0 GB'

    def test_size_human_none_when_missing(self):
        op = BackupOperationFactory(size_bytes=None)
        assert op.size_human is None


class TestBackupOperationStr:
    def test_str_contains_id_and_status(self):
        op = BackupOperationFactory(status='success', hostname='db-01')
        assert f'#{op.id}' in str(op)
        assert 'success' in str(op)