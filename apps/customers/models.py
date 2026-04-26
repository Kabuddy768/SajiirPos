from django.db import models

class Customer(models.Model):
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, unique=True, null=True, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    loyalty_points = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.phone})"
