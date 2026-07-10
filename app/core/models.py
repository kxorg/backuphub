import uuid
from django.db import models
from django.utils import timezone

# LOOKUP TABLES (DICTIONARIES)

class SystemType(models.Model):
    
    """
    SYSTEM_TYPE - Lookup table for system types
    (PostgreSQL, GitLab, Kubernetes, etc.)
    """
    name = models.CharField(
        max_length=255,
        unique=True,
        verbose_name='System type name'
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name='Description'
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
        verbose_name = 'System Type'
        verbose_name_plural = 'System Types'
        ordering = ['name']

    def __str__(self):
        return self.name


class Environment(models.Model):
    """
    ENVIRONMENT - Lookup table for environments
    (Production, Test, Development)
    """
    name = models.CharField(
        max_length=255,
        unique=True,
        verbose_name='Environment name'
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name='Description'
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
        verbose_name = 'Environment'
        verbose_name_plural = 'Environments'
        ordering = ['name']

    def __str__(self):
        return self.name


class BackupTool(models.Model):
    """
    BACKUP_TOOL - Lookup table for backup tools
    (pg_dump, Velero, rsync, etc.)
    """
    name = models.CharField(
        max_length=255,
        unique=True,
        verbose_name='Tool name'
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
        verbose_name = 'Backup Tool'
        verbose_name_plural = 'Backup Tools'
        ordering = ['name']

    def __str__(self):
        return self.name


# TARGET SYSTEMS AND VERSIONS

class TargetSystem(models.Model):
    """
    TARGET_SYSTEM - Target system for backup
    (specific server or service)
    """
    system_type = models.ForeignKey(
        SystemType,
        on_delete=models.PROTECT,
        related_name='target_systems',
        verbose_name='System type'
    )
    environment = models.ForeignKey(
        Environment,
        on_delete=models.PROTECT,
        related_name='target_systems',
        verbose_name='Environment',
        null=True,      # ← Добавь
        blank=True      # ← Добавь
)
    name = models.CharField(
        max_length=255,
        verbose_name='System name'
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name='Description'
    )
    api_key = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
        verbose_name='API Key',
        help_text='Automatically generated upon creation.'
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
        verbose_name = 'Target System'
        verbose_name_plural = 'Target Systems'
        ordering = ['name']

    def __str__(self):
        return f"{self.name}"

    @property
    def current_version(self):
        """Returns the current version of the system."""
        return self.versions.filter(is_current=True).first()


class TargetSystemVersion(models.Model):
    """
    TARGET_SYSTEM_VERSION - Target system version
    (change history with owner/administrator tracking)
    """
    target_system = models.ForeignKey(
        TargetSystem,
        on_delete=models.CASCADE,
        related_name='versions',
        verbose_name='Target system'
    )
    version_number = models.PositiveIntegerField(
        verbose_name='Version number'
    )
    owner = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='Owner'
    )
    administrator = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='Administrator'
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
        verbose_name = 'System Version'
        verbose_name_plural = 'System Versions'
        ordering = ['target_system', '-version_number']
        unique_together = ['target_system', 'version_number']

    def __str__(self):
        return f"{self.target_system.name} v{self.version_number}"


# BACKUP CONFIGURATIONS AND VERSIONS

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


# BACKUP OPERATIONS

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
