from django.db import models
from django.conf import settings


ROLE_CHOICES = [
    ('owner', 'Owner'),
    ('admin', 'Admin'),
    ('manager', 'Manager'),
    ('cashier', 'Cashier'),
    ('auditor', 'Auditor'),
]


class Branch(models.Model):
    name = models.CharField(max_length=150)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    etims_branch_code = models.CharField(max_length=50, blank=True)
    etims_device_serial = models.CharField(max_length=100, blank=True)
    
    # M-Pesa Daraja Settings (per branch)
    mpesa_env = models.CharField(
        max_length=20,
        choices=[('sandbox', 'Sandbox'), ('production', 'Production')],
        default='sandbox'
    )
    mpesa_shortcode = models.CharField(max_length=50, blank=True)
    mpesa_consumer_key = models.CharField(max_length=255, blank=True)
    mpesa_consumer_secret = models.CharField(max_length=255, blank=True)
    mpesa_passkey = models.CharField(max_length=255, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class StaffProfile(models.Model):
    """
    Links a user to a specific branch with a branch-level role.

    TenantUser.role acts as the ceiling; StaffProfile.branch_role is the
    effective role for that specific branch.  branch_role must never exceed
    the ceiling defined by TenantUser.role.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='staff_profiles',
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name='staff_members',
    )
    is_active = models.BooleanField(default=True)
    branch_role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='cashier',
        help_text='Effective role for this branch. Cannot exceed the TenantUser.role ceiling.',
    )

    class Meta:
        unique_together = ('user', 'branch')

    def __str__(self):
        return f"{self.user.email} — {self.branch_role} at {self.branch.name}"
