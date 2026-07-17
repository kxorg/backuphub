import pytest
from app.celery import debug_task, config_loggers

pytestmark = pytest.mark.django_db


class TestCeleryTasks:
    def test_debug_task_runs(self):
        debug_task.apply()

    def test_config_loggers_callable(self):
        config_loggers()