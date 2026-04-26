from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.sales.views import SaleViewSet, ProductLookupViewSet, CashSessionViewSet
from apps.payments.views import MpesaViewSet

router = DefaultRouter()
router.register(r'sales', SaleViewSet, basename='sale')
router.register(r'products', ProductLookupViewSet, basename='product')
router.register(r'sessions', CashSessionViewSet, basename='session')
router.register(r'mpesa', MpesaViewSet, basename='mpesa')

urlpatterns = [
    path('', include(router.urls)),
]
