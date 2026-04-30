from django.db import models
from django.conf import settings

class BranchStock(models.Model):
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='branch_stocks')
    branch = models.ForeignKey('branches.Branch', on_delete=models.CASCADE, related_name='stocks')
    quantity = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('product', 'branch')

    def __str__(self):
        return f"{self.product.name} at {self.branch.name}: {self.quantity}"

class StockMovement(models.Model):
    REASON_CHOICES = [
        ('sale', 'Sale'),
        ('return', 'Return'),
        ('purchase', 'Purchase'),
        ('adjustment', 'Adjustment'),
        ('spoilage', 'Spoilage'),
        ('expiry', 'Expiry'),
        ('theft', 'Theft'),
        ('damage', 'Damage'),
        ('transfer_in', 'Transfer In'),
        ('transfer_out', 'Transfer Out'),
        ('opening', 'Opening'),
    ]

    product = models.ForeignKey('products.Product', on_delete=models.PROTECT, related_name='movements')
    branch = models.ForeignKey('branches.Branch', on_delete=models.PROTECT, related_name='movements')
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    quantity_before = models.DecimalField(max_digits=12, decimal_places=3)
    quantity_after = models.DecimalField(max_digits=12, decimal_places=3)
    
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)
    reference_id = models.CharField(max_length=100, blank=True)
    
    batch = models.ForeignKey('products.ProductBatch', on_delete=models.SET_NULL, null=True, blank=True, related_name='movements')
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='stock_movements')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.reason} - {self.product.name} ({self.quantity})"


class StockTransfer(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('shipped', 'Shipped'),
        ('received', 'Received'),
        ('cancelled', 'Cancelled'),
    ]

    transfer_number = models.CharField(max_length=100, unique=True)
    from_branch = models.ForeignKey('branches.Branch', on_delete=models.PROTECT, related_name='transfers_out')
    to_branch = models.ForeignKey('branches.Branch', on_delete=models.PROTECT, related_name='transfers_in')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    notes = models.TextField(blank=True)

    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='transfer_requests')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='transfer_approvals')
    shipped_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='transfer_shipments')
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='transfer_receipts')

    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.transfer_number}: {self.from_branch} → {self.to_branch}"


class StockTransferItem(models.Model):
    transfer = models.ForeignKey(StockTransfer, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT, related_name='transfer_items')
    quantity_requested = models.DecimalField(max_digits=12, decimal_places=3)
    quantity_shipped = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    quantity_received = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    batch = models.ForeignKey('products.ProductBatch', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.product.name} — req: {self.quantity_requested}"
