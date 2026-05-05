from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.sales.views import SaleViewSet, ProductLookupViewSet, CashSessionViewSet
from apps.payments.views import MpesaViewSet
from apps.returns.views import ReturnViewSet
from apps.inventory.views import StockTransferViewSet
from apps.expenses.views import ExpenseViewSet, ExpenseCategoryViewSet
from apps.customers.views import CustomerViewSet
from apps.purchasing.views import SupplierViewSet, PurchaseOrderViewSet, GoodsReceivedNoteViewSet

router = DefaultRouter()
router.register(r'sales', SaleViewSet, basename='sale')
router.register(r'products', ProductLookupViewSet, basename='product')
router.register(r'sessions', CashSessionViewSet, basename='session')
router.register(r'mpesa', MpesaViewSet, basename='mpesa')
router.register(r'returns', ReturnViewSet, basename='return')
router.register(r'transfers', StockTransferViewSet, basename='transfer')
router.register(r'expenses', ExpenseViewSet, basename='expense')
router.register(r'expense-categories', ExpenseCategoryViewSet, basename='expense-category')
router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'suppliers', SupplierViewSet, basename='supplier')
router.register(r'purchase-orders', PurchaseOrderViewSet, basename='purchase-order')
router.register(r'grns', GoodsReceivedNoteViewSet, basename='grn')

urlpatterns = [
    path('', include(router.urls)),
    path('reports/', include('apps.reports.urls')),
]
