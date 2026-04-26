from django.contrib import admin
from .models import Sale, SaleItem


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    readonly_fields = ['subtotal']


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ['receipt_number', 'branch', 'cashier', 'total_amount', 'payment_method', 'status', 'created_at']
    list_filter = ['status', 'payment_method', 'branch']
    search_fields = ['receipt_number', 'cashier__email']
    readonly_fields = ['created_at', 'receipt_number']
    inlines = [SaleItemInline]
