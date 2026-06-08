from rest_framework import serializers
from .models import Customer

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = [
            'id', 'name', 'phone', 'email', 'address', 'loyalty_points', 
            'is_active', 'created_at', 'allow_credit_sales', 'credit_limit', 
            'current_credit_balance'
        ]
        read_only_fields = ['loyalty_points', 'current_credit_balance', 'created_at']
