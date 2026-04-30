from django.db import models
from django.conf import settings

class Branch(models.Model):
    name = models.CharField(max_length=150)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    etims_branch_code = models.CharField(max_length=50, blank=True)
    etims_device_serial = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class StaffProfile(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='staff_profiles')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='staff_members')
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.user.email} at {self.branch.name}"
