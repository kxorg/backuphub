from django.contrib import admin
from .models import (
    TargetSystem,
    TargetSystemVersion,
)


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

