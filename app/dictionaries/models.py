from django.db import models


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

