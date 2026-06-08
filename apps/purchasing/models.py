from django.db import models
from django.conf import settings

class Supplier(models.Model):
    name = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    kra_pin = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    # Running outstanding amount owed to this supplier
    current_payable_balance = models.DecimalField(
        max_digits=14, decimal_places=2, default=0.00,
        help_text='Total unpaid amount across all GRNs.'
    )

    def __str__(self):
        return self.name

class PurchaseOrder(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('partial', 'Partially Received'),
        ('received', 'Received'),
        ('cancelled', 'Cancelled'),
    ]

    order_number = models.CharField(max_length=100, unique=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='orders')
    branch = models.ForeignKey('branches.Branch', on_delete=models.CASCADE, related_name='orders')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    expected_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='purchase_orders', null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.order_number

class PurchaseOrderItem(models.Model):
    order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT)
    quantity_ordered = models.DecimalField(max_digits=12, decimal_places=3)
    purchase_unit = models.ForeignKey('products.Unit', on_delete=models.PROTECT)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2)
    quantity_received_sale_units = models.DecimalField(max_digits=12, decimal_places=3, default=0)

    def __str__(self):
        return f"{self.quantity_ordered}x {self.product.name}"

class GoodsReceivedNote(models.Model):
    PAYMENT_TERM_CHOICES = [
        ('cash', 'Cash (Paid on Purchase)'),
        ('credit', 'Credit (Account)'),
    ]

    grn_number = models.CharField(max_length=100, unique=True)
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.SET_NULL, null=True, blank=True, related_name='grns')
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='grns')
    branch = models.ForeignKey('branches.Branch', on_delete=models.PROTECT, related_name='grns')
    
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='received_grns')
    supplier_invoice_number = models.CharField(max_length=100, blank=True)
    
    payment_term = models.CharField(max_length=20, choices=PAYMENT_TERM_CHOICES, default='credit')
    due_date = models.DateField(null=True, blank=True, help_text="Due date if purchased on credit")
    
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def total_value(self):
        return sum(item.quantity_purchase_units * item.unit_cost for item in self.items.all())

    def __str__(self):
        return self.grn_number


class GRNItem(models.Model):
    grn = models.ForeignKey(GoodsReceivedNote, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT)
    
    quantity_purchase_units = models.DecimalField(max_digits=12, decimal_places=3)
    purchase_unit = models.ForeignKey('products.Unit', on_delete=models.PROTECT)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2)
    
    quantity_sale_units = models.DecimalField(max_digits=12, decimal_places=3, editable=False)
    cost_per_sale_unit = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    
    expiry_date = models.DateField(null=True, blank=True)
    batch_number = models.CharField(max_length=100, blank=True)

    def save(self, *args, **kwargs):
        self.quantity_sale_units = self.quantity_purchase_units * self.product.units_per_purchase
        self.cost_per_sale_unit = self.unit_cost / self.product.units_per_purchase
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity_purchase_units}x {self.product.name} (GRN {self.grn.grn_number})"


class SupplierPayment(models.Model):
    """Records a payment made to a supplier against a GRN or general account."""
    METHOD_CHOICES = [
        ('cash',          'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('mpesa',         'M-Pesa Business'),
        ('cheque',        'Cheque'),
    ]

    supplier          = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='payments')
    grn               = models.ForeignKey(
        GoodsReceivedNote, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='supplier_payments',
        help_text='Link to the specific GRN this payment settles (optional).'
    )
    amount            = models.DecimalField(max_digits=14, decimal_places=2)
    payment_method    = models.CharField(max_length=20, choices=METHOD_CHOICES, default='bank_transfer')
    transaction_reference = models.CharField(max_length=100, blank=True)
    notes             = models.TextField(blank=True)
    paid_by           = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='supplier_payments'
    )
    paid_at           = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-paid_at']

    def __str__(self):
        return f"{self.supplier.name} — KES {self.amount} ({self.get_payment_method_display()})"
