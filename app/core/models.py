import uuid
from django.db import models

class TargetSystem(models.Model):
    name = models.CharField(max_length=100, verbose_name='Name')
    system_type = models.CharField(max_length=50, verbose_name='Type')
    api_key = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name='API-key')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created at')

    class Meta:
        db_table = 'target_system'

    def __str__(self):
        return self.name


class Host(models.Model):
    hostname = models.CharField(max_length=255, verbose_name='Hostname')
    ip_address = models.GenericIPAddressField(verbose_name='IP Address')
    target_system = models.ForeignKey(
        TargetSystem, 
        on_delete=models.CASCADE, 
        related_name='hosts',
        verbose_name='Target System'
    )

    class Meta:
        db_table = 'host'

    def __str__(self):
        return f"{self.hostname} ({self.ip_address})"


class Backup(models.Model):
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('error', 'Error'),
        ('in_progress', 'In Progress'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name='Operation ID')
    host = models.ForeignKey(Host, on_delete=models.SET_NULL, null=True, blank=True, related_name='backups', verbose_name='Server')
    target_system = models.ForeignKey(TargetSystem, on_delete=models.CASCADE, related_name='backups', verbose_name='System')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, verbose_name='Status')
    start_time = models.DateTimeField(verbose_name='Start Time')
    end_time = models.DateTimeField(null=True, blank=True, verbose_name='End Time')
    backup_size = models.BigIntegerField(null=True, blank=True, verbose_name='Size (bytes)')
    storage = models.CharField(max_length=255, null=True, blank=True, verbose_name='Storage Path')
    
    meta_data = models.JSONField(default=dict, blank=True, verbose_name='Technical Data')
    error_message = models.TextField(null=True, blank=True, verbose_name='Error Message')
    
    class Meta:
        db_table = 'backup'

    @property
    def duration(self):
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None