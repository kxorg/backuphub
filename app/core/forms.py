from django import forms
from .models import TargetSystem, BackupConfiguration, BackupConfigurationVersion, SystemType, Environment, BackupTool


class TargetSystemForm(forms.ModelForm):
    """
    Combined form for TargetSystem with versioned fields
    """
    owner = forms.CharField(
        max_length=255,
        required=False,
        label='Owner',
        help_text='System owner (versioned field)'
    )
    administrator = forms.CharField(
        max_length=255,
        required=False,
        label='Administrator',
        help_text='System administrator (versioned field)'
    )

    class Meta:
        model = TargetSystem
        fields = [
            'system_type',
            'environment',
            'name',
            'description',
            'is_active',
            'owner',
            'administrator',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # При редактировании заполняем поля owner и administrator из текущей версии
        if self.instance and self.instance.pk:
            current_version = self.instance.current_version
            if current_version:
                self.fields['owner'].initial = current_version.owner or ''
                self.fields['administrator'].initial = current_version.administrator or ''


class BackupConfigurationForm(forms.ModelForm):
    """
    Combined form for BackupConfiguration with versioned fields
    """
    # Поля из BackupConfigurationVersion
    backup_tool = forms.ModelChoiceField(
        queryset=BackupTool.objects.filter(is_active=True),
        required=True,
        label='Backup Tool'
    )
    backup_mode = forms.ChoiceField(
        choices=BackupConfigurationVersion.BACKUP_MODE_CHOICES,
        required=True,
        label='Backup Mode'
    )
    schedule_cron = forms.CharField(
        max_length=100,
        required=False,
        label='Schedule (cron)',
        help_text='Cron expression for backup schedule'
    )
    retention_days = forms.IntegerField(
        min_value=1,
        required=True,
        label='Retention Period (days)'
    )
    rpo_minutes = forms.IntegerField(
        min_value=1,
        required=True,
        label='RPO (minutes)'
    )
    rto_minutes = forms.IntegerField(
        min_value=1,
        required=True,
        label='RTO (minutes)'
    )
    storage_type = forms.ChoiceField(
        choices=BackupConfigurationVersion.STORAGE_TYPE_CHOICES,
        required=True,
        label='Storage Type'
    )
    storage_path = forms.CharField(
        max_length=500,
        required=False,
        label='Storage Path'
    )
    verify_after_backup = forms.BooleanField(
        required=False,
        label='Verify After Backup'
    )
    immutable_storage = forms.BooleanField(
        required=False,
        label='Immutable Storage'
    )

    class Meta:
        model = BackupConfiguration
        fields = [
            'target_system_version',
            'name',
            'description',
            'is_active',
            'backup_tool',
            'backup_mode',
            'schedule_cron',
            'retention_days',
            'rpo_minutes',
            'rto_minutes',
            'storage_type',
            'storage_path',
            'verify_after_backup',
            'immutable_storage',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # При редактировании заполняем поля из текущей версии
        if self.instance and self.instance.pk:
            current_version = self.instance.current_version
            if current_version:
                self.fields['backup_tool'].initial = current_version.backup_tool
                self.fields['backup_mode'].initial = current_version.backup_mode
                self.fields['schedule_cron'].initial = current_version.schedule_cron
                self.fields['retention_days'].initial = current_version.retention_days
                self.fields['rpo_minutes'].initial = current_version.rpo_minutes
                self.fields['rto_minutes'].initial = current_version.rto_minutes
                self.fields['storage_type'].initial = current_version.storage_type
                self.fields['storage_path'].initial = current_version.storage_path
                self.fields['verify_after_backup'].initial = current_version.verify_after_backup
                self.fields['immutable_storage'].initial = current_version.immutable_storage

class SystemTypeForm(forms.ModelForm):
    class Meta:
        model = SystemType
        fields = ['name', 'description']


class EnvironmentForm(forms.ModelForm):
    class Meta:
        model = Environment
        fields = ['name', 'description']


class BackupToolForm(forms.ModelForm):
    class Meta:
        model = BackupTool
        fields = ['name', 'description', 'is_active']