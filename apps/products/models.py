from django.db import models
from django.conf import settings

class Category(models.Model):
    name = models.CharField(max_length=150)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')

    def __str__(self):
        return self.name

class Unit(models.Model):
    name = models.CharField(max_length=50, unique=True)
    short_name = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.short_name

class Product(models.Model):
    TAX_TYPE_CHOICES = [
        ('V', 'Standard VAT 16%'),
        ('E', 'VAT Exempt'),
        ('Z', 'Zero-rated'),
    ]

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    sku = models.CharField(max_length=100, unique=True)
    barcode = models.CharField(max_length=100, unique=True, null=True, blank=True)
    
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    tax_type = models.CharField(max_length=1, choices=TAX_TYPE_CHOICES, default='V')
    is_tax_inclusive = models.BooleanField(default=True)
    
    sale_unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name='sale_products')
    purchase_unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name='purchase_products', null=True, blank=True)
    units_per_purchase = models.DecimalField(max_digits=10, decimal_places=3, default=1)
    
    minimum_stock_level = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    reorder_quantity = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    
    track_expiry = models.BooleanField(default=False)
    expiry_alert_days = models.PositiveIntegerField(default=30)
    
    is_active = models.BooleanField(default=True)
    is_weighable = models.BooleanField(default=False)
    allow_discount = models.BooleanField(default=True)
    
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='created_products')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class ProductBatch(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='batches')
    branch = models.ForeignKey('branches.Branch', on_delete=models.CASCADE, related_name='product_batches')
    batch_number = models.CharField(max_length=100)
    expiry_date = models.DateField()
    quantity_remaining = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    is_written_off = models.BooleanField(default=False)
    received_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.name} - {self.batch_number}"
