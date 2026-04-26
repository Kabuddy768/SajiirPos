from django.db import models

class Payment(models.Model):
    METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('mpesa', 'M-Pesa'),
        ('card', 'Card'),
        ('store_credit', 'Store Credit'),
        ('bank_transfer', 'Bank Transfer'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('failed', 'Failed'),
        ('reversed', 'Reversed'),
    ]

    sale = models.ForeignKey('sales.Sale', on_delete=models.CASCADE, related_name='payments')
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    mpesa_phone = models.CharField(max_length=20, blank=True)
    mpesa_checkout_request_id = models.CharField(max_length=100, blank=True)
    mpesa_merchant_request_id = models.CharField(max_length=100, blank=True)
    mpesa_receipt_number = models.CharField(max_length=100, blank=True)
    
    card_last4 = models.CharField(max_length=4, blank=True)
    card_reference = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.method} - {self.amount} ({self.status})"
