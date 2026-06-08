from django import forms
from .models import Product, Category, Unit

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'description', 'category', 'primary_supplier', 'sku', 'barcode',
            'cost_price', 'selling_price', 'tax_type', 'is_tax_inclusive',
            'sale_unit', 'purchase_unit', 'units_per_purchase',
            'minimum_stock_level', 'reorder_quantity', 'track_expiry',
            'expiry_alert_days', 'is_active', 'is_weighable', 'allow_discount',
            'image'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add some styling classes if needed, though we use global CSS for dashboard
        for field_name, field in self.fields.items():
            if field.required:
                field.label = f"{field.label} *"
