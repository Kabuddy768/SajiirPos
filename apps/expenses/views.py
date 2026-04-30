from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from apps.tenants.permissions import IsCashier
from .models import Expense, ExpenseCategory
from .serializers import ExpenseSerializer, ExpenseCategorySerializer


class ExpenseCategoryViewSet(viewsets.ModelViewSet):
    queryset = ExpenseCategory.objects.all()
    serializer_class = ExpenseCategorySerializer
    permission_classes = [IsAuthenticated, IsCashier]


class ExpenseViewSet(viewsets.ModelViewSet):
    queryset = Expense.objects.select_related('branch', 'category', 'recorded_by').all()
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated, IsCashier]

    def perform_create(self, serializer):
        serializer.save(recorded_by=self.request.user)
