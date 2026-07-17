from django import forms
from .models import BackupConfiguration, BackupConfigurationVersion
from dictionaries.models import BackupTool

class BackupConfigurationForm(forms.ModelForm):
    """
    Combined form for BackupConfiguration with versioned fields
    """

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
        widgets = {
            'target_system_version': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': ''}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': ''}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name in ['target_system_version', 'name', 'description']:
                continue
                
            if isinstance(field.widget, (forms.Select, forms.NullBooleanSelect)):
                field.widget.attrs.update({'class': 'form-select'})
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-check-input'})
            else:
                field.widget.attrs.update({'class': 'form-control'})

        if 'schedule_cron' in self.fields:
            self.fields['schedule_cron'].widget.attrs.update({'placeholder': ''})
        if 'storage_path' in self.fields:
            self.fields['storage_path'].widget.attrs.update({'placeholder': ''})

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

