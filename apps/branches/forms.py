from django import forms
from .models import Branch

class BranchForm(forms.ModelForm):
    class Meta:
        model = Branch
        fields = [
            'name', 'address', 'phone', 
            'etims_branch_code', 'etims_device_serial', 
            'mpesa_env', 'mpesa_shortcode', 'mpesa_consumer_key', 
            'mpesa_consumer_secret', 'mpesa_passkey', 
            'is_active'
        ]
        widgets = {
            'address': forms.Textarea(attrs={'rows': 2}),
            'mpesa_consumer_secret': forms.TextInput(attrs={'type': 'text', 'placeholder': 'Consumer Secret'}),
            'mpesa_passkey': forms.TextInput(attrs={'type': 'text', 'placeholder': 'Lipa Na M-Pesa Passkey'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field.required:
                field.label = f"{field.label} *"
