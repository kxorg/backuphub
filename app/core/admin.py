# from django.contrib import admin
# from .models import SystemType, TargetSystem, Host, Backup


# @admin.register(SystemType)
# class SystemTypeAdmin(admin.ModelAdmin):
#     list_display = ('id', 'name', 'description', 'created_at')
#     search_fields = ('name',)
#     list_filter = ('created_at',)


# @admin.register(TargetSystem)
# class TargetSystemAdmin(admin.ModelAdmin):
#     list_display = ('id', 'name', 'system_type', 'api_key', 'created_at')
#     list_filter = ('system_type', 'created_at')
#     search_fields = ('name', 'api_key')
#     readonly_fields = ('api_key', 'created_at')


# @admin.register(Host)
# class HostAdmin(admin.ModelAdmin):
#     list_display = ('id', 'hostname', 'ip_address', 'target_system')
#     list_filter = ('target_system',)
#     search_fields = ('hostname', 'ip_address')


# @admin.register(Backup)
# class BackupAdmin(admin.ModelAdmin):
#     list_display = ('id', 'get_hostname', 'get_system_name', 'status', 'start_time', 'end_time', 'backup_size')
#     list_filter = ('status', 'start_time', 'target_system')
#     search_fields = ('id', 'host__hostname', 'target_system__name')
#     readonly_fields = ('id', 'start_time', 'end_time', 'duration')
#     date_hierarchy = 'start_time'

#     @admin.display(description='Hostname')
#     def get_hostname(self, obj):
#         return obj.host.hostname if obj.host else '-'

#     @admin.display(description='System Name')
#     def get_system_name(self, obj):
#         return obj.target_system.name if obj.target_system else '-'

from django.contrib import admin
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


# ==========================================
# LOOKUP TABLES (DICTIONARIES)
# ==========================================

@admin.register(SystemType)
class SystemTypeAdmin(admin.ModelAdmin):
    """Admin interface for SystemType model."""
    list_display = ('id', 'name', 'description', 'created_at', 'created_by')
    search_fields = ('name', 'description')
    ordering = ('name',)
    list_per_page = 25
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('System Type Information', {
            'fields': ('name', 'description')
        }),
        ('Audit', {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Environment)
class EnvironmentAdmin(admin.ModelAdmin):
    """Admin interface for Environment model."""
    list_display = ('id', 'name', 'description', 'created_at', 'created_by')
    search_fields = ('name', 'description')
    ordering = ('name',)
    list_per_page = 25
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Environment Information', {
            'fields': ('name', 'description')
        }),
        ('Audit', {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(BackupTool)
class BackupToolAdmin(admin.ModelAdmin):
    """Admin interface for BackupTool model."""
    list_display = ('id', 'name', 'description', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    ordering = ('name',)
    list_per_page = 25
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Tool Information', {
            'fields': ('name', 'description', 'is_active')
        }),
        ('Audit', {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


# ==========================================
# TARGET SYSTEMS AND VERSIONS
# ==========================================

class TargetSystemVersionInline(admin.TabularInline):
    """Inline editor for TargetSystemVersion."""
    model = TargetSystemVersion
    extra = 0
    fields = ('version_number', 'owner', 'administrator', 'is_current', 'valid_from', 'valid_to', 'created_by')
    readonly_fields = ('created_at',)
    ordering = ('-version_number',)
    show_change_link = True


@admin.register(TargetSystem)
class TargetSystemAdmin(admin.ModelAdmin):
    """Admin interface for TargetSystem model."""
    list_display = ('id', 'name', 'system_type', 'environment', 'api_key_short', 'is_active', 'created_at')
    list_filter = ('is_active', 'system_type', 'environment')
    search_fields = ('name', 'description', 'api_key')
    ordering = ('name',)
    list_per_page = 25
    readonly_fields = ('api_key', 'created_at', 'updated_at')
    inlines = [TargetSystemVersionInline]

    fieldsets = (
        ('System Information', {
            'fields': ('name', 'system_type', 'environment', 'description')
        }),
        ('Ownership', {
            'fields': ('owner', 'administrator')
        }),
        ('API Access', {
            'fields': ('api_key',),
            'description': 'API key is automatically generated and cannot be edited manually.'
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Audit', {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def api_key_short(self, obj):
        """Display shortened API key for security."""
        if obj.api_key:
            return f"{str(obj.api_key)[:8]}..."
        return "-"
    api_key_short.short_description = 'API Key'
    api_key_short.admin_order_field = 'api_key'


@admin.register(TargetSystemVersion)
class TargetSystemVersionAdmin(admin.ModelAdmin):
    """Admin interface for TargetSystemVersion model."""
    list_display = ('id', 'target_system', 'version_number', 'owner', 'administrator', 'is_current', 'valid_from', 'valid_to')
    list_filter = ('is_current', 'target_system')
    search_fields = ('target_system__name', 'owner', 'administrator')
    ordering = ('target_system', '-version_number')
    list_per_page = 25
    readonly_fields = ('created_at',)

    fieldsets = (
        ('Version Information', {
            'fields': ('target_system', 'version_number', 'is_current')
        }),
        ('Ownership', {
            'fields': ('owner', 'administrator')
        }),
        ('Validity Period', {
            'fields': ('valid_from', 'valid_to')
        }),
        ('Audit', {
            'fields': ('created_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )


# ==========================================
# BACKUP CONFIGURATIONS AND VERSIONS
# ==========================================

class BackupConfigurationVersionInline(admin.TabularInline):
    """Inline editor for BackupConfigurationVersion."""
    model = BackupConfigurationVersion
    extra = 0
    fields = (
        'version_number', 'backup_tool', 'backup_mode', 'schedule_cron',
        'retention_days', 'rpo_minutes', 'rto_minutes', 'is_current',
        'valid_from', 'valid_to'
    )
    readonly_fields = ('created_at',)
    ordering = ('-version_number',)
    show_change_link = True


@admin.register(BackupConfiguration)
class BackupConfigurationAdmin(admin.ModelAdmin):
    """Admin interface for BackupConfiguration model."""
    list_display = ('id', 'name', 'target_system_version', 'is_active', 'created_at')
    list_filter = ('is_active', 'target_system_version__target_system')
    search_fields = ('name', 'description')
    ordering = ('name',)
    list_per_page = 25
    readonly_fields = ('created_at', 'updated_at')
    inlines = [BackupConfigurationVersionInline]

    fieldsets = (
        ('Configuration Information', {
            'fields': ('name', 'target_system_version', 'description')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Audit', {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(BackupConfigurationVersion)
class BackupConfigurationVersionAdmin(admin.ModelAdmin):
    """Admin interface for BackupConfigurationVersion model."""
    list_display = (
        'id', 'backup_configuration', 'version_number', 'backup_tool',
        'backup_mode', 'schedule_cron', 'retention_days', 'rpo_minutes',
        'rto_minutes', 'is_current', 'valid_from'
    )
    list_filter = ('is_current', 'backup_mode', 'storage_type', 'backup_tool')
    search_fields = ('backup_configuration__name',)
    ordering = ('backup_configuration', '-version_number')
    list_per_page = 25
    readonly_fields = ('created_at',)

    fieldsets = (
        ('Version Information', {
            'fields': ('backup_configuration', 'version_number', 'backup_tool', 'is_current')
        }),
        ('Backup Settings', {
            'fields': ('backup_mode', 'schedule_cron', 'retention_days')
        }),
        ('Business Metrics', {
            'fields': ('rpo_minutes', 'rto_minutes'),
            'description': 'RPO = Recovery Point Objective, RTO = Recovery Time Objective'
        }),
        ('Storage', {
            'fields': ('storage_type', 'storage_path', 'verify_after_backup', 'immutable_storage')
        }),
        ('Validity Period', {
            'fields': ('valid_from', 'valid_to')
        }),
        ('Audit', {
            'fields': ('created_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )


# ==========================================
# BACKUP OPERATIONS
# ==========================================

@admin.register(BackupOperation)
class BackupOperationAdmin(admin.ModelAdmin):
    """Admin interface for BackupOperation model."""
    list_display = (
        'id', 'backup_configuration_version', 'hostname', 'status',
        'started_at', 'finished_at', 'duration_display', 'size_display',
        'created_at'
    )
    list_filter = ('status', 'backup_configuration_version__backup_configuration', 'storage_type')
    search_fields = ('hostname', 'ip_address', 'external_job_id', 'error_message')
    ordering = ('-started_at',)
    list_per_page = 50
    readonly_fields = ('created_at', 'duration_seconds', 'size_human')
    date_hierarchy = 'started_at'

    fieldsets = (
        ('Operation Information', {
            'fields': ('backup_configuration_version', 'external_job_id', 'status')
        }),
        ('Host Information', {
            'fields': ('hostname', 'ip_address')
        }),
        ('Timing', {
            'fields': ('started_at', 'finished_at', 'duration_seconds')
        }),
        ('Storage', {
            'fields': ('storage_type', 'storage_path', 'size_bytes', 'size_human')
        }),
        ('Result', {
            'fields': ('metadata', 'error_message')
        }),
        ('Audit', {
            'fields': ('created_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )

    def duration_display(self, obj):
        """Display duration in human-readable format."""
        if obj.duration_seconds is None:
            return "-"
        minutes, seconds = divmod(obj.duration_seconds, 60)
        if minutes > 0:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"
    duration_display.short_description = 'Duration'
    duration_display.admin_order_field = 'started_at'

    def size_display(self, obj):
        """Display size in human-readable format."""
        return obj.size_human or "-"
    size_display.short_description = 'Size'
    size_display.admin_order_field = 'size_bytes'

    actions = ['mark_as_success', 'mark_as_error']

    def mark_as_success(self, request, queryset):
        """Bulk action: Mark selected operations as success."""
        updated = queryset.update(status='success')
        self.message_user(request, f'{updated} operations marked as success.')
    mark_as_success.short_description = 'Mark selected operations as success'

    def mark_as_error(self, request, queryset):
        """Bulk action: Mark selected operations as error."""
        updated = queryset.update(status='error')
        self.message_user(request, f'{updated} operations marked as error.')
    mark_as_error.short_description = 'Mark selected operations as error'


# ==========================================
# ADMIN SITE CUSTOMIZATION
# ==========================================

admin.site.site_header = 'BackupHub Administration'
admin.site.site_title = 'BackupHub Admin'
admin.site.index_title = 'Backup Management System'