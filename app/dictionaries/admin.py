from django.contrib import admin
from .models import SystemType, Environment, BackupTool, InformationSystem


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


@admin.register(InformationSystem)
class InformationSystemAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'description', 'created_at')
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(BackupTool)
class BackupToolAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'description', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)
    ordering = ('name',)
