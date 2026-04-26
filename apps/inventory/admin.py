from django.contrib import admin
from .models import BranchStock, StockMovement

@admin.register(BranchStock)
class BranchStockAdmin(admin.ModelAdmin):
    list_display = ['product', 'branch', 'quantity', 'updated_at']
    list_filter = ['branch']
    search_fields = ['product__name', 'branch__name']
    readonly_fields = ['quantity', 'updated_at']

@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ['product', 'branch', 'reason', 'quantity',
                    'quantity_before', 'quantity_after', 'performed_by', 'created_at']
    list_filter = ['reason', 'branch']
    search_fields = ['product__name', 'branch__name', 'reference_id']
    readonly_fields = ['created_at', 'quantity_before', 'quantity_after']
