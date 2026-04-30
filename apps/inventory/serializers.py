from rest_framework import serializers
from .models import StockTransfer, StockTransferItem


class StockTransferItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = StockTransferItem
        fields = [
            'id', 'product', 'product_name',
            'quantity_requested', 'quantity_shipped', 'quantity_received',
            'batch',
        ]
        read_only_fields = ['id', 'quantity_shipped', 'quantity_received']


class StockTransferSerializer(serializers.ModelSerializer):
    items = StockTransferItemSerializer(many=True, read_only=True)
    from_branch_name = serializers.CharField(source='from_branch.name', read_only=True)
    to_branch_name = serializers.CharField(source='to_branch.name', read_only=True)
    requested_by_email = serializers.CharField(source='requested_by.email', read_only=True)

    class Meta:
        model = StockTransfer
        fields = [
            'id', 'transfer_number', 'from_branch', 'from_branch_name',
            'to_branch', 'to_branch_name', 'status', 'notes',
            'requested_by', 'requested_by_email',
            'approved_by', 'shipped_by', 'received_by',
            'created_at', 'approved_at', 'shipped_at', 'received_at',
            'items',
        ]
        read_only_fields = [
            'id', 'transfer_number', 'status', 'requested_by',
            'approved_by', 'shipped_by', 'received_by',
            'created_at', 'approved_at', 'shipped_at', 'received_at',
        ]


# --- Input serializers ---

class TransferItemInputSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3)
    batch_id = serializers.IntegerField(required=False, allow_null=True, default=None)


class TransferCreateSerializer(serializers.Serializer):
    from_branch_id = serializers.IntegerField()
    to_branch_id = serializers.IntegerField()
    items = TransferItemInputSerializer(many=True)
    notes = serializers.CharField(required=False, allow_blank=True, default='')


class TransferActionSerializer(serializers.Serializer):
    """Used for approve / ship / receive / cancel actions."""
    # Ship and receive can optionally override quantities per item
    quantities = serializers.DictField(
        child=serializers.DecimalField(max_digits=12, decimal_places=3),
        required=False,
        default=None,
    )
