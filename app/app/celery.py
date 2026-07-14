from __future__ import absolute_import
import os

from celery import Celery
from celery.schedules import crontab
from celery.signals import setup_logging
from django.conf import settings

import logging
from logging.config import dictConfig

logger = logging.getLogger("celery")

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")
broker = os.getenv("CELERY_BROKER_URL")
backend = os.getenv("CELERY_RESULT_BACKEND")

app = Celery(
    "app",
    broker=broker,
    backend=backend,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    timezone="Europe/Moscow",
)
# app.control.purge()

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.

# Load task modules from all registered Django apps.
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
# app.conf.worker_log_format = (
#     "%(levelname)s|%(asctime)s|%(module)s|%(process)d|%(thread)d|%(message)s"
# )
app.conf.beat_scheduler = 'django_celery_beat.schedulers:DatabaseScheduler'

# app.conf.beat_schedule = {
#     "send_morning_report": {
#         "task": "xxxxxxxxxxxxxxxxx.xxxxxxxxxxxxxxxxx",
#         # "schedule": crontab(hour=5, minute=00),
#         "schedule": crontab(minute='*/1'),
#     }
# }
"""
crontab() - every minute
crontab(minute=0, hour='*') - every hour
crontab(minute='*/15') - every 15 minutes
crontab(minute=0, hour='*/3') - every 3 hours
crontab(minute=0, hour=0) - daily at midnight
"""


@setup_logging.connect
def config_loggers(*args, **kwargs):
    dictConfig(settings.LOGGING)


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
