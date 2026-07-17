from django.contrib import admin
from django.utils.html import format_html
from .models import (
    BackupOperation,
)

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