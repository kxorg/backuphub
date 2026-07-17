from django.db import models
from systems.models import TargetSystemVersion
from dictionaries.models import BackupTool
from django.utils import timezone


class BackupConfiguration(models.Model):
    """
    BACKUP_CONFIGURATION - Logical group of backup settings
    """
    target_system_version = models.ForeignKey(
        TargetSystemVersion,
        on_delete=models.PROTECT,
        related_name='backup_configurations',
        verbose_name='System version'
    )
    name = models.CharField(
        max_length=255,
        verbose_name='Configuration name'
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name='Description'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Active'
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
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Updated at'
    )
    updated_by = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='Updated by'
    )

    class Meta:
        verbose_name = 'Backup Configuration'
        verbose_name_plural = 'Backup Configurations'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.target_system_version.target_system.name})"

    @property
    def current_version(self):
        """Returns the current version of the configuration."""
        return self.versions.filter(is_current=True).first()


class BackupConfigurationVersion(models.Model):
    """
    BACKUP_CONFIGURATION_VERSION - Backup configuration version
    (specific parameters: tool, mode, RPO/RTO, storage, etc.)
    """
    BACKUP_MODE_CHOICES = [
        ('full', 'Full'),
        ('incremental', 'Incremental'),
        ('differential', 'Differential'),
        ('physical', 'Physical'),
        ('logical', 'Logical'),
    ]

    STORAGE_TYPE_CHOICES = [
        ('local', 'Local'),
        ('s3', 'Amazon S3'),
        ('azure', 'Azure Blob Storage'),
        ('gcs', 'Google Cloud Storage'),
        ('nfs', 'NFS'),
        ('other', 'Other'),
    ]

    backup_configuration = models.ForeignKey(
        BackupConfiguration,
        on_delete=models.CASCADE,
        related_name='versions',
        verbose_name='Backup configuration'
    )
    backup_tool = models.ForeignKey(
        BackupTool,
        on_delete=models.PROTECT,
        related_name='configuration_versions',
        verbose_name='Backup tool'
    )
    version_number = models.PositiveIntegerField(
        verbose_name='Version number'
    )
    backup_mode = models.CharField(
        max_length=50,
        choices=BACKUP_MODE_CHOICES,
        default='full',
        verbose_name='Backup mode'
    )
    schedule_cron = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Schedule (cron)'
    )
    retention_days = models.PositiveIntegerField(
        default=30,
        verbose_name='Retention period (days)'
    )
    rpo_minutes = models.PositiveIntegerField(
        default=1440,
        verbose_name='RPO (minutes)'
    )
    rto_minutes = models.PositiveIntegerField(
        default=60,
        verbose_name='RTO (minutes)'
    )
    storage_type = models.CharField(
        max_length=50,
        choices=STORAGE_TYPE_CHOICES,
        default='local',
        verbose_name='Storage type'
    )
    storage_path = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name='Storage path'
    )
    verify_after_backup = models.BooleanField(
        default=False,
        verbose_name='Verify after backup'
    )
    immutable_storage = models.BooleanField(
        default=False,
        verbose_name='Immutable storage'
    )
    is_current = models.BooleanField(
        default=False,
        verbose_name='Is current'
    )
    valid_from = models.DateTimeField(
        default=timezone.now,
        verbose_name='Valid from'
    )
    valid_to = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Valid to'
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
        verbose_name = 'Backup Configuration Version'
        verbose_name_plural = 'Backup Configuration Versions'
        ordering = ['backup_configuration', '-version_number']
        unique_together = ['backup_configuration', 'version_number']

    def __str__(self):
        return f"{self.backup_configuration.name} v{self.version_number} ({self.backup_tool.name})"

