from rest_framework import serializers
from .models import Expense, ExpenseCategory


class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = ['id', 'name']


class ExpenseSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True, default=None)
    recorded_by_email = serializers.CharField(source='recorded_by.email', read_only=True)

    class Meta:
        model = Expense
        fields = [
            'id', 'branch', 'category', 'category_name',
            'description', 'amount', 'paid_on', 'receipt_image',
            'recorded_by', 'recorded_by_email', 'created_at',
        ]
        read_only_fields = ['id', 'recorded_by', 'created_at']
