from rest_framework import serializers
from .models import Return, ReturnItem


class ReturnItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='sale_item.product.name', read_only=True)

    class Meta:
        model = ReturnItem
        fields = ['id', 'sale_item', 'product_name', 'quantity', 'unit_price', 'line_total']
        read_only_fields = ['id', 'unit_price', 'line_total']


class ReturnSerializer(serializers.ModelSerializer):
    items = ReturnItemSerializer(many=True, read_only=True)
    original_sale_number = serializers.CharField(source='original_sale.sale_number', read_only=True)
    processed_by_email = serializers.CharField(source='processed_by.email', read_only=True)
    approved_by_email = serializers.CharField(source='approved_by.email', read_only=True, default=None)

    class Meta:
        model = Return
        fields = [
            'id', 'return_number', 'original_sale', 'original_sale_number',
            'branch', 'processed_by', 'processed_by_email',
            'approved_by', 'approved_by_email',
            'reason', 'notes', 'refund_amount', 'refund_method',
            'created_at', 'items',
        ]
        read_only_fields = [
            'id', 'return_number', 'branch', 'processed_by',
            'refund_amount', 'created_at',
        ]


class ReturnItemInputSerializer(serializers.Serializer):
    sale_item_id = serializers.IntegerField()
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3)


class ReturnCreateSerializer(serializers.Serializer):
    """
    Payload the cashier POSTs to create a return.
    """
    original_sale_id = serializers.IntegerField()
    items = ReturnItemInputSerializer(many=True)
    reason = serializers.ChoiceField(choices=Return.REASON_CHOICES)
    refund_method = serializers.ChoiceField(choices=[
        ('cash', 'Cash'),
        ('mpesa', 'M-Pesa'),
        ('credit_note', 'Credit Note'),
    ])
    notes = serializers.CharField(required=False, allow_blank=True, default='')
    approved_by_id = serializers.IntegerField(required=False, allow_null=True, default=None)
