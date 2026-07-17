from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import BackupOperation
from .tasks import send_backup_alert

@receiver(post_save, sender=BackupOperation)
def trigger_backup_alert(sender, instance, **kwargs):
    target_statuses = ['error', 'warning', 'cancelled']
    
    if instance.status in target_statuses:
        try:
            config_version = instance.backup_configuration_version
            config = config_version.backup_configuration
            system = config.target_system_version.target_system
            
            config_name = config.name
            system_name = system.name
        except AttributeError:
            config_name = "Unknown_Config"
            system_name = "Unknown_System"

        send_backup_alert.delay(
            instance.status,
            instance.id,
            system_name,
            config_name
        )