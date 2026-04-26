from django.contrib import admin
from .models import Category, Product, ProductVariant


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'category', 'unit_price', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['name', 'sku', 'barcode']


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ['product', 'name', 'sku', 'price_modifier']
    search_fields = ['product__name', 'name', 'sku']
