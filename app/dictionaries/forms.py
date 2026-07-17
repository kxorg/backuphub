from django import forms
from .models import SystemType, Environment, BackupTool, InformationSystem


class SystemTypeForm(forms.ModelForm):
    class Meta:
        model = SystemType
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': ''}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': ''}),
        }


class EnvironmentForm(forms.ModelForm):
    class Meta:
        model = Environment
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': ''}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': ''}),
        }


class BackupToolForm(forms.ModelForm):
    class Meta:
        model = BackupTool
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': ''}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': ''}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class InformationSystemForm(forms.ModelForm):
    class Meta:
        model = InformationSystem
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': ''}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': ''}),
        }
