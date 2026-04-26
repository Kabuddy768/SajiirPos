from django.db import models
from django.conf import settings

class Return(models.Model):
    REASON_CHOICES = [
        ('wrong_item', 'Wrong Item'),
        ('defective', 'Defective'),
        ('customer_change', 'Customer Changed Mind'),
        ('other', 'Other'),
    ]

    return_number = models.CharField(max_length=100, unique=True)
    original_sale = models.ForeignKey('sales.Sale', on_delete=models.PROTECT, related_name='returns')
    branch = models.ForeignKey('branches.Branch', on_delete=models.CASCADE, related_name='returns')
    
    processed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='processed_returns')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_returns')
    
    reason = models.CharField(max_length=50, choices=REASON_CHOICES)
    notes = models.TextField(blank=True)
    
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    refund_method = models.CharField(max_length=50)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.return_number

class ReturnItem(models.Model):
    return_obj = models.ForeignKey(Return, on_delete=models.CASCADE, related_name='items')
    sale_item = models.ForeignKey('sales.SaleItem', on_delete=models.PROTECT, related_name='returned_items')
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.quantity}x of {self.sale_item.product.name}"
