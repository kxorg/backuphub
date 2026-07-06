from django.contrib import admin
from .models import TargetSystem, Host, Backup


@admin.register(TargetSystem)
class TargetSystemAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'system_type', 'api_key', 'created_at']
    list_filter = ['system_type', 'created_at']
    search_fields = ['name', 'system_type']
    readonly_fields = ['api_key', 'created_at']


@admin.register(Host)
class HostAdmin(admin.ModelAdmin):
    list_display = ['id', 'hostname', 'ip_address', 'target_system']
    list_filter = ['target_system']
    search_fields = ['hostname', 'ip_address']


@admin.register(Backup)
class BackupAdmin(admin.ModelAdmin):
    list_display = ['id', 'hostname', 'system_name', 'status', 'start_time', 'end_time']
    list_filter = ['status', 'start_time', 'target_system']
    search_fields = ['id', 'hostname', 'system_name']
    readonly_fields = ['id', 'start_time', 'end_time', 'duration']
    date_hierarchy = 'start_time'

    def hostname(self, obj):
        return obj.host.hostname if obj.host else '-'
    
    def system_name(self, obj):
        return obj.target_system.name if obj.target_system else '-'