from rest_framework import serializers
from .models import Supplier, PurchaseOrder, PurchaseOrderItem, GoodsReceivedNote, GRNItem

class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = '__all__'

class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseOrderItem
        fields = ['id', 'product', 'quantity_ordered', 'purchase_unit', 'unit_cost', 'quantity_received_sale_units']
        read_only_fields = ['quantity_received_sale_units']

class PurchaseOrderSerializer(serializers.ModelSerializer):
    items = PurchaseOrderItemSerializer(many=True)

    class Meta:
        model = PurchaseOrder
        fields = ['id', 'order_number', 'supplier', 'branch', 'status', 'expected_date', 'notes', 'created_by', 'created_at', 'items']
        read_only_fields = ['status', 'created_by', 'created_at']

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        user = self.context['request'].user
        validated_data['created_by'] = user
        order = PurchaseOrder.objects.create(**validated_data)
        for item_data in items_data:
            PurchaseOrderItem.objects.create(order=order, **item_data)
        return order

class GRNItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = GRNItem
        fields = ['id', 'product', 'quantity_purchase_units', 'purchase_unit', 'unit_cost', 'expiry_date', 'batch_number']

class GoodsReceivedNoteSerializer(serializers.ModelSerializer):
    items = GRNItemSerializer(many=True)

    class Meta:
        model = GoodsReceivedNote
        fields = ['id', 'grn_number', 'purchase_order', 'supplier', 'branch', 'received_by', 'supplier_invoice_number', 'notes', 'created_at', 'items']
        read_only_fields = ['received_by', 'created_at']

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        user = self.context['request'].user
        validated_data['received_by'] = user
        grn = GoodsReceivedNote.objects.create(**validated_data)
        for item_data in items_data:
            GRNItem.objects.create(grn=grn, **item_data)
        
        # Call service to apply stock/batch
        from .services import GRNService
        GRNService.receive(grn)
        
        return grn
