from rest_framework import serializers
from .models import Sale, SaleItem, CashSession
from apps.products.models import Product
from apps.payments.models import Payment

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'barcode', 'selling_price', 'cost_price', 'is_tax_inclusive', 'tax_type', 'is_active']

class CartItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3)
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2)
    discount_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)
    batch_id = serializers.IntegerField(required=False, allow_null=True)

class PaymentInputSerializer(serializers.Serializer):
    method = serializers.CharField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    mpesa_phone = serializers.CharField(required=False, allow_blank=True)
    card_reference = serializers.CharField(required=False, allow_blank=True)

class SaleCreateSerializer(serializers.Serializer):
    session_id = serializers.IntegerField()
    customer_id = serializers.IntegerField(required=False, allow_null=True)
    client_created_at = serializers.DateTimeField()
    offline_uuid = serializers.UUIDField()
    cart = CartItemSerializer(many=True)
    payments = PaymentInputSerializer(many=True)
    manager_override = serializers.BooleanField(required=False, default=False)

class SaleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sale
        fields = '__all__'

class CashSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashSession
        fields = '__all__'
