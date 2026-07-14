from django.contrib import admin 
from .models import (
    BackupConfiguration,
    BackupConfigurationVersion,
)

class BackupConfigurationVersionInline(admin.TabularInline):
    model = BackupConfigurationVersion
    extra = 0
    fields = (
        'version_number', 'backup_tool', 'backup_mode', 'schedule_cron',
        'retention_days', 'rpo_minutes', 'rto_minutes', 'is_current'
    )
    ordering = ('-version_number',)


@admin.register(BackupConfiguration)
class BackupConfigurationAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'target_system_version', 'is_active', 'created_at')
    list_filter = ('is_active',)
    inlines = [BackupConfigurationVersionInline]


@admin.register(BackupConfigurationVersion)
class BackupConfigurationVersionAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'backup_configuration', 'version_number', 'backup_tool',
        'backup_mode', 'rpo_minutes', 'rto_minutes', 'is_current'
    )
    list_filter = ('is_current', 'backup_mode', 'backup_tool')
