from django.contrib import admin
from .models import Return, ReturnItem


class ReturnItemInline(admin.TabularInline):
    model = ReturnItem
    extra = 0
    readonly_fields = ['sale_item', 'quantity', 'unit_price', 'line_total']
    can_delete = False


@admin.register(Return)
class ReturnAdmin(admin.ModelAdmin):
    list_display = [
        'return_number', 'original_sale', 'branch',
        'refund_amount', 'refund_method', 'reason',
        'processed_by', 'approved_by', 'created_at',
    ]
    list_filter = ['reason', 'refund_method', 'branch']
    search_fields = ['return_number', 'original_sale__sale_number', 'processed_by__email']
    readonly_fields = ['return_number', 'created_at']
    inlines = [ReturnItemInline]
