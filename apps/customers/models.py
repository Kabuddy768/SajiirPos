from django.db import models

class LoyaltyTier(models.Model):
    name = models.CharField(max_length=50)
    min_points = models.IntegerField(default=0)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    
    def __str__(self):
        return self.name

class Customer(models.Model):
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, unique=True, null=True, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    loyalty_points = models.IntegerField(default=0)
    tier = models.ForeignKey(LoyaltyTier, on_delete=models.SET_NULL, null=True, blank=True)
    last_purchase_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.phone})"
