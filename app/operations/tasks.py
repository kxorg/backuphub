import logging
from celery import shared_task

logger = logging.getLogger("celery")

@shared_task(name="operations.tasks.send_backup_alert")
def send_backup_alert(status, backup_id, system_name, config_name):
    message = f"BACKUP {status} {backup_id} {system_name} {config_name}, SENDING ALERT EMAIL TO ADMINS"
    
    logger.warning(message)
    
    return message