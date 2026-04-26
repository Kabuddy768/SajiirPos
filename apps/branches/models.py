from django.db import models

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
