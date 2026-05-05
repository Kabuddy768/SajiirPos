from django.db import models
from django.conf import settings

class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('deactivate', 'Deactivate'),
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('void_sale', 'Void Sale'),
        ('approve_return', 'Approve Return'),
        ('adjust_stock', 'Adjust Stock'),
        ('write_off', 'Write Off'),
        ('open_session', 'Open Session'),
        ('close_session', 'Close Session'),
        ('price_change', 'Price Change'),
        ('transfer', 'Transfer'),
    ]

    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    branch = models.ForeignKey('branches.Branch', on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    before_data = models.JSONField(null=True, blank=True)
    after_data = models.JSONField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action} on {self.model_name}:{self.object_id} by {self.user}"

class Notification(models.Model):
    TYPE_CHOICES = [
        ('expiry', 'Expiry Alert'),
        ('low_stock', 'Low Stock Alert'),
        ('general', 'General Notification'),
    ]

    type = models.CharField(max_length=50, choices=TYPE_CHOICES, default='general')
    title = models.CharField(max_length=255)
    message = models.TextField()
    branch = models.ForeignKey('branches.Branch', on_delete=models.CASCADE, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.type}] {self.title}"
