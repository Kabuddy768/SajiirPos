from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.sales.views import SaleViewSet, ProductLookupViewSet, CashSessionViewSet
from apps.payments.views import MpesaViewSet
from apps.returns.views import ReturnViewSet
from apps.inventory.views import StockTransferViewSet
from apps.expenses.views import ExpenseViewSet, ExpenseCategoryViewSet
from apps.customers.views import CustomerViewSet
from apps.purchasing.views import SupplierViewSet, PurchaseOrderViewSet, GoodsReceivedNoteViewSet
from apps.audit.views import AuditViewSet

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
router.register(r'audit', AuditViewSet, basename='audit')

from api.v1.sync import SyncSalesView

from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache

def health_check(request):
    checks = {
        'status': 'ok',
        'database': 'unknown',
        'cache': 'unknown',
        'schema': connection.schema_name,
    }
    
    try:
        connection.ensure_connection()
        checks['database'] = 'ok'
    except Exception as e:
        checks['database'] = f'error: {str(e)}'
        checks['status'] = 'degraded'
    
    try:
        cache.set('health_check', 'ok', 10)
        val = cache.get('health_check')
        checks['cache'] = 'ok' if val == 'ok' else 'miss'
    except Exception as e:
        checks['cache'] = f'error: {str(e)}'
        checks['status'] = 'degraded'
    
    status_code = 200 if checks['status'] == 'ok' else 503
    return JsonResponse(checks, status=status_code)

urlpatterns = [
    path('', include(router.urls)),
    path('reports/', include('apps.reports.urls')),
    path('sync/sales/', SyncSalesView.as_view(), name='sync-sales'),
    path('health/', health_check, name='health_check'),
]

