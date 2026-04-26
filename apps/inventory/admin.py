from django.contrib import admin
from .models import BranchStock, StockMovement


@admin.register(BranchStock)
class BranchStockAdmin(admin.ModelAdmin):
    list_display = ['product', 'branch', 'quantity', 'reorder_level', 'updated_at']
    list_filter = ['branch']
    search_fields = ['product__name', 'branch__name']


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ['product', 'branch', 'movement_type', 'quantity', 'quantity_after', 'created_by', 'created_at']
    list_filter = ['movement_type', 'branch']
    search_fields = ['product__name', 'branch__name', 'reference']
    readonly_fields = ['created_at']
