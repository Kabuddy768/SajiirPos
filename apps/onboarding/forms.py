from django import forms
from django.contrib.auth import get_user_model
import re

User = get_user_model()

# Subdomains that are reserved for infrastructure use
RESERVED_SUBDOMAINS = {
    'www', 'api', 'admin', 'billing', 'support', 'portal', 'mail',
    'ftp', 'ssh', 'test', 'staging', 'demo', 'app', 'dashboard',
    'static', 'media', 'cdn', 'login', 'sajiirpos', 'sajiir',
}


class TenantRegisterForm(forms.Form):
    """Step 1: Owner account creation."""
    first_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'placeholder': 'First name',
            'autocomplete': 'given-name',
        })
    )
    last_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'placeholder': 'Last name',
            'autocomplete': 'family-name',
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'placeholder': 'you@business.com',
            'autocomplete': 'email',
        })
    )
    password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Min. 8 characters',
            'autocomplete': 'new-password',
        })
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Repeat password',
            'autocomplete': 'new-password',
        })
    )

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                'An account with this email already exists. '
                'Please log in or use a different email.'
            )
        return email

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password')
        p2 = cleaned.get('password_confirm')
        if p1 and p2 and p1 != p2:
            self.add_error('password_confirm', 'Passwords do not match.')
        return cleaned


class WorkspaceSetupForm(forms.Form):
    """Step 2: Workspace (tenant) creation details."""
    business_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g. Karen Supermarket',
            'autocomplete': 'organization',
        })
    )
    subdomain = forms.SlugField(
        max_length=40,
        widget=forms.TextInput(attrs={
            'placeholder': 'karensupermarket',
            'autocomplete': 'off',
        }),
        help_text='Only lowercase letters, numbers, and hyphens. This becomes your login URL.'
    )
    plan = forms.ChoiceField(
        choices=[
            ('starter', 'Starter — KES 2,500/mo'),
            ('pro',     'Pro — KES 6,500/mo'),
            ('enterprise', 'Enterprise — Custom Pricing'),
        ],
        widget=forms.RadioSelect,
        initial='starter',
    )

    def clean_subdomain(self):
        sub = self.cleaned_data['subdomain'].strip().lower()

        # Must be at least 3 characters
        if len(sub) < 3:
            raise forms.ValidationError('Workspace name must be at least 3 characters.')

        # Must not start or end with a hyphen
        if sub.startswith('-') or sub.endswith('-'):
            raise forms.ValidationError('Workspace name cannot start or end with a hyphen.')

        # Only alphanumeric + hyphens
        if not re.match(r'^[a-z0-9][a-z0-9\-]{1,38}[a-z0-9]$', sub):
            raise forms.ValidationError(
                'Workspace name may only contain lowercase letters, numbers, and hyphens.'
            )

        # Reserved subdomain check
        if sub in RESERVED_SUBDOMAINS:
            raise forms.ValidationError(
                f'"{sub}" is a reserved name and cannot be used. Please choose a different name.'
            )

        # Uniqueness check against existing tenants
        from apps.tenants.models import Tenant
        if Tenant.objects.filter(schema_name=sub).exists():
            raise forms.ValidationError(
                f'The workspace "{sub}" is already taken. Please choose a different name.'
            )

        return sub
