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
