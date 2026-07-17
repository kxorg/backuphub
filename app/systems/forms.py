from django import forms
from .models import TargetSystem


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
            'information_system',
            'name',
            'description',
            'is_active',
            'owner',
            'administrator',
        ]
        widgets = {
                'system_type': forms.Select(attrs={'class': 'form-select'}),
                'environment': forms.Select(attrs={'class': 'form-select'}),
                'information_system': forms.Select(attrs={'class': 'form-select'}),
                
                'name': forms.TextInput(attrs={
                    'class': 'form-control', 
                    'placeholder': 'Enter system name...'
                }),
                'description': forms.Textarea(attrs={
                    'class': 'form-control', 
                    'rows': 4, 
                    'placeholder': ''
                }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # When editing, fill in the owner and administrator fields from the current version.
        if self.instance and self.instance.pk:
            current_version = self.instance.current_version
            if current_version:
                self.fields['owner'].initial = current_version.owner or ''
                self.fields['administrator'].initial = current_version.administrator or ''
