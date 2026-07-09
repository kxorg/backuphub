from django.contrib import admin
from django.utils.html import format_html
from .models import (
    SystemType,
    Environment,
    BackupTool,
    TargetSystem,
    TargetSystemVersion,
    BackupConfiguration,
    BackupConfigurationVersion,
    BackupOperation,
)

@admin.register(SystemType)
class SystemTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'description', 'created_at')
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(Environment)
class EnvironmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'description', 'created_at')
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(BackupTool)
class BackupToolAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'description', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)
    ordering = ('name',)


class TargetSystemVersionInline(admin.TabularInline):
    model = TargetSystemVersion
    extra = 0
    fields = ('version_number', 'owner', 'administrator', 'is_current', 'valid_from', 'valid_to')
    readonly_fields = ('created_at',)
    ordering = ('-version_number',)


@admin.register(TargetSystem)
class TargetSystemAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'system_type', 'environment', 'api_key_short', 'is_active', 'created_at')
    list_filter = ('is_active', 'system_type', 'environment')
    search_fields = ('name', 'api_key')
    readonly_fields = ('api_key', 'created_at', 'updated_at')
    inlines = [TargetSystemVersionInline]

    fieldsets = (
        ('System Information', {'fields': ('name', 'system_type', 'environment', 'description')}),
        ('API Access', {
            'fields': ('api_key',),
            'description': 'API key is automatically generated.'
        }),
        ('Status', {'fields': ('is_active',)}),
    )

    def api_key_short(self, obj):
        if obj.api_key:
            return f"{str(obj.api_key)[:8]}..."
        return "-"
    api_key_short.short_description = 'API Key'


@admin.register(TargetSystemVersion)
class TargetSystemVersionAdmin(admin.ModelAdmin):
    list_display = ('id', 'target_system', 'version_number', 'owner', 'is_current', 'valid_from')
    list_filter = ('is_current', 'target_system')


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


@admin.register(BackupOperation)
class BackupOperationAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'status_badge', 'hostname', 'system_name', 'tool_name',
        'started_at', 'duration_display', 'size_display'
    )
    list_filter = ('status', 'started_at')
    search_fields = ('hostname', 'external_job_id')
    readonly_fields = ('created_at', 'duration_seconds', 'size_human')
    date_hierarchy = 'started_at'

    fieldsets = (
        ('Operation', {'fields': ('backup_configuration_version', 'external_job_id', 'status')}),
        ('Host', {'fields': ('hostname', 'ip_address')}),
        ('Timing', {'fields': ('started_at', 'finished_at', 'duration_seconds')}),
        ('Storage', {'fields': ('storage_type', 'storage_path', 'size_bytes', 'size_human')}),
        ('Result', {'fields': ('metadata', 'error_message')}),
    )

    def status_badge(self, obj):
        colors = {'success': '#28a745', 'error': '#dc3545', 'in_progress': '#ffc107'}
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background:{}; color:white; padding:3px 8px; border-radius:4px; font-weight:bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def system_name(self, obj):
        return obj.backup_configuration_version.backup_configuration.target_system_version.target_system.name
    system_name.short_description = 'System'

    def tool_name(self, obj):
        return obj.backup_configuration_version.backup_tool.name
    tool_name.short_description = 'Tool'

    def duration_display(self, obj):
        if obj.duration_seconds is None:
            return "-"
        minutes, seconds = divmod(obj.duration_seconds, 60)
        return f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
    duration_display.short_description = 'Duration'

    def size_display(self, obj):
        return obj.size_human or "-"
    size_display.short_description = 'Size'


admin.site.site_header = 'BackupHub Administration'
admin.site.site_title = 'BackupHub Admin'
admin.site.index_title = 'Backup Management System'