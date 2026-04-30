from django.contrib import admin
from .models import BranchStock, StockMovement, StockTransfer, StockTransferItem

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


class StockTransferItemInline(admin.TabularInline):
    model = StockTransferItem
    extra = 0
    readonly_fields = ['quantity_shipped', 'quantity_received']


@admin.register(StockTransfer)
class StockTransferAdmin(admin.ModelAdmin):
    list_display = [
        'transfer_number', 'from_branch', 'to_branch', 'status',
        'requested_by', 'created_at',
    ]
    list_filter = ['status', 'from_branch', 'to_branch']
    search_fields = ['transfer_number']
    readonly_fields = [
        'transfer_number', 'created_at', 'approved_at',
        'shipped_at', 'received_at',
    ]
    inlines = [StockTransferItemInline]

