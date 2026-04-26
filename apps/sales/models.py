from django.db import models
from django.conf import settings
import uuid

class CashSession(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('closed', 'Closed'),
    ]

    branch = models.ForeignKey('branches.Branch', on_delete=models.CASCADE, related_name='cash_sessions')
    cashier = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cash_sessions')
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    opening_float = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    closing_float = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='open')
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Session {self.id} - {self.cashier.email}"

class Sale(models.Model):
    STATUS_CHOICES = [
        ('completed', 'Completed'),
        ('voided', 'Voided'),
        ('refunded', 'Refunded'),
        ('partial_refund', 'Partial Refund'),
    ]

    SUBMISSION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('submitted', 'Submitted'),
        ('failed', 'Failed'),
    ]

    sale_number = models.CharField(max_length=100, unique=True)
    session = models.ForeignKey(CashSession, on_delete=models.PROTECT, related_name='sales')
    branch = models.ForeignKey('branches.Branch', on_delete=models.CASCADE, related_name='sales')
    cashier = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sales')
    customer = models.ForeignKey('customers.Customer', on_delete=models.SET_NULL, null=True, blank=True, related_name='sales')
    
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    taxable_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')
    
    # eTIMS
    etims_invoice_number = models.CharField(max_length=100, blank=True)
    etims_signed_at = models.DateTimeField(null=True, blank=True)
    etims_qr_code = models.TextField(blank=True)
    etims_signature = models.CharField(max_length=255, blank=True)
    etims_submission_status = models.CharField(max_length=20, choices=SUBMISSION_STATUS_CHOICES, default='pending')
    
    # Offline sync
    client_created_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    synced_at = models.DateTimeField(auto_now_add=True)
    is_offline_sale = models.BooleanField(default=False)
    offline_uuid = models.UUIDField(unique=True, default=uuid.uuid4)

    def __str__(self):
        return self.sale_number

class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT, related_name='sale_items')
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)
    
    tax_type = models.CharField(max_length=1, default='V')
    batch = models.ForeignKey('products.ProductBatch', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"
