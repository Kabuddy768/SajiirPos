from rest_framework import serializers
from .models import Sale, SaleItem, CashSession
from apps.products.models import Product
from apps.payments.models import Payment

class ProductSerializer(serializers.ModelSerializer):
    current_stock = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'name', 'barcode', 'selling_price', 'cost_price', 'is_tax_inclusive', 'tax_type', 'is_active', 'current_stock']

    def get_current_stock(self, obj):
        from apps.inventory.models import BranchStock
        from apps.branches.models import StaffProfile
        
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return 0
            
        try:
            profile = StaffProfile.objects.filter(user=request.user, is_active=True).first()
            if profile:
                bs = BranchStock.objects.filter(
                    product=obj, 
                    branch=profile.branch
                ).first()
                return float(bs.quantity) if bs else 0
        except:
            pass
        return 0

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
    send_digital_receipt = serializers.BooleanField(required=False, default=False)
    receipt_phone = serializers.CharField(required=False, allow_blank=True, allow_null=True)

class SaleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sale
        fields = '__all__'

class CashSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashSession
        fields = '__all__'
