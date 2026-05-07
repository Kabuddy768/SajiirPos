import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
import datetime


class StaffInvitation(models.Model):
    """
    Represents an invitation sent by an Owner/Admin to join a tenant as staff.

    Flow:
      1. Owner/Admin creates an invitation (email + role + optional branch).
      2. System emails a unique token link to the invitee.
      3. Invitee clicks the link, sees an accept page.
         - If account exists → straight redirect to login then dashboard.
         - If new user → prompted to set password.
      4. On accept, TenantUser + StaffProfile are created, token marked used.
    """

    email = models.EmailField()
    role = models.CharField(
        max_length=20,
        choices=[
            ('owner', 'Owner'),
            ('admin', 'Admin'),
            ('manager', 'Manager'),
            ('cashier', 'Cashier'),
            ('auditor', 'Auditor'),
        ],
        default='cashier',
    )
    # Branch is optional — Owners/Admins don't need a specific branch
    branch = models.ForeignKey(
        'branches.Branch',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='pending_invitations',
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='sent_invitations',
    )
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Invitation for {self.email} ({self.role}) — {'used' if self.is_used else 'pending'}"

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + datetime.timedelta(hours=48)
        super().save(*args, **kwargs)

    @property
    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at
