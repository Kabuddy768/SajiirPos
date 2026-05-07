from django import forms
from apps.branches.models import Branch
from .models import StaffInvitation


ROLE_CHOICES_INVITABLE = [
    ('admin', 'Admin'),
    ('manager', 'Manager'),
    ('cashier', 'Cashier'),
    ('auditor', 'Auditor'),
]


class InviteStaffForm(forms.Form):
    """Form used by Owner/Admin to send an invitation."""
    email = forms.EmailField(
        label='Email Address',
        widget=forms.EmailInput(attrs={
            'placeholder': 'colleague@example.com',
            'id': 'id_email',
        }),
    )
    role = forms.ChoiceField(
        choices=ROLE_CHOICES_INVITABLE,
        label='Role',
        widget=forms.Select(attrs={'id': 'id_role'}),
    )
    branch = forms.ModelChoiceField(
        queryset=Branch.objects.filter(is_active=True),
        required=False,
        empty_label='— No specific branch (Owner/Admin) —',
        label='Branch',
        widget=forms.Select(attrs={'id': 'id_branch'}),
    )


class AcceptInvitationForm(forms.Form):
    """Form shown to a new invitee to set their name and password."""
    first_name = forms.CharField(
        max_length=150,
        label='First Name',
        widget=forms.TextInput(attrs={'placeholder': 'First name', 'id': 'id_first_name'}),
    )
    last_name = forms.CharField(
        max_length=150,
        label='Last Name',
        widget=forms.TextInput(attrs={'placeholder': 'Last name', 'id': 'id_last_name'}),
    )
    password = forms.CharField(
        label='Create Password',
        min_length=8,
        widget=forms.PasswordInput(attrs={'placeholder': '••••••••', 'id': 'id_password'}),
    )
    confirm_password = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={'placeholder': '••••••••', 'id': 'id_confirm_password'}),
    )

    def clean(self):
        cleaned = super().clean()
        pw = cleaned.get('password')
        cpw = cleaned.get('confirm_password')
        if pw and cpw and pw != cpw:
            raise forms.ValidationError('Passwords do not match.')
        return cleaned
