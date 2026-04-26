from django.contrib import admin
from .models import Sale, SaleItem, CashSession

class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    readonly_fields = ['product', 'quantity', 'unit_price', 'cost_price',
                       'tax_amount', 'line_total']
    can_delete = False

@admin.register(CashSession)
class CashSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'branch', 'cashier', 'status', 'opened_at',
                    'opening_float', 'closing_float']
    list_filter = ['status', 'branch']
    readonly_fields = ['opened_at']

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ['sale_number', 'branch', 'cashier', 'total_amount',
                    'status', 'etims_submission_status', 'client_created_at']
    list_filter = ['status', 'etims_submission_status', 'branch', 'is_offline_sale']
    search_fields = ['sale_number', 'cashier__email']
    readonly_fields = ['sale_number', 'offline_uuid', 'created_at',
                       'client_created_at', 'synced_at']
    inlines = [SaleItemInline]
