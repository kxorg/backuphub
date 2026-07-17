import uuid
from django.db import models
from django.utils import timezone
from dictionaries.models import SystemType, Environment


# Create your models here.

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
