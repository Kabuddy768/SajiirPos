from django.contrib import admin
from .models import Category, Unit, Product, ProductBatch

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent']
    search_fields = ['name']

@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ['name', 'short_name']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'barcode', 'category', 'selling_price',
                    'cost_price', 'tax_type', 'is_active', 'is_weighable']
    list_filter = ['is_active', 'tax_type', 'track_expiry', 'category']
    search_fields = ['name', 'sku', 'barcode']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(ProductBatch)
class ProductBatchAdmin(admin.ModelAdmin):
    list_display = ['product', 'branch', 'batch_number', 'expiry_date',
                    'quantity_remaining', 'is_written_off']
    list_filter = ['is_written_off', 'branch']
    search_fields = ['product__name', 'batch_number']
