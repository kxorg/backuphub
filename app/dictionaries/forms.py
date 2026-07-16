from django import forms
from .models import SystemType, Environment, BackupTool, InformationSystem


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


class InformationSystemForm(forms.ModelForm):
    class Meta:
        model = InformationSystem
        fields = ['name', 'description']