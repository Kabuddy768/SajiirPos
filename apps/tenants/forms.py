from django import forms
from apps.tenants.models import Tenant

class TenantSettingsForm(forms.ModelForm):
    class Meta:
        model = Tenant
        fields = [
            'name', 'contact_email', 'contact_phone', 
            'country', 'currency', 'kra_pin', 
            'etims_serial', 'vat_registered', 'vat_registration_no'
        ]
        widgets = {
            'vat_registered': forms.CheckboxInput(attrs={'style': 'width: auto; margin-right: 8px;'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name != 'vat_registered':
                field.widget.attrs.update({'style': 'width: 100%; padding: 8px 12px; border-radius: 6px; border: 1px solid var(--border); background: var(--surface); color: var(--text);'})
            if field.required:
                field.label = f"{field.label} *"
