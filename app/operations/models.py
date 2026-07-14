from django.db import models
from configurations.models import BackupConfigurationVersion

class BackupOperation(models.Model):
    """
    BACKUP_OPERATION - Backup execution fact (result)
    """
    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('success', 'Success'),
        ('error', 'Error'),
        ('warning', 'Warning'),
        ('cancelled', 'Cancelled'),
    ]

    backup_configuration_version = models.ForeignKey(
        BackupConfigurationVersion,
        on_delete=models.PROTECT,
        related_name='operations',
        verbose_name='Configuration version'
    )
    external_job_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='External job ID'
    )
    hostname = models.CharField(
        max_length=255,
        blank = True,
        verbose_name='Hostname'
    )
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        verbose_name='IP address'
    )
    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default='in_progress',
        verbose_name='Status'
    )
    started_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Started at'
    )
    finished_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Finished at'
    )
    size_bytes = models.BigIntegerField(
        blank=True,
        null=True,
        verbose_name='Size (bytes)'
    )
    storage_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='Storage type'
    )
    storage_path = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name='Backup file path'
    )
    metadata = models.JSONField(
        blank=True,
        null=True,
        verbose_name='Metadata'
    )
    error_message = models.TextField(
        blank=True,
        null=True,
        verbose_name='Error message'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created at'
    )
    created_by = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='Created by'
    )

    class Meta:
        verbose_name = 'Backup Operation'
        verbose_name_plural = 'Backup Operations'
        ordering = ['-started_at']

    def __str__(self):
        return f"Operation #{self.id} - {self.status} ({self.hostname})"

    @property
    def duration_seconds(self):
        """Calculates backup duration in seconds."""
        if self.started_at and self.finished_at:
            delta = self.finished_at - self.started_at
            return int(delta.total_seconds())
        return None

    @property
    def size_human(self):
        """Human-readable backup size."""
        if self.size_bytes is None:
            return None
        size = self.size_bytes
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if abs(size) < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"