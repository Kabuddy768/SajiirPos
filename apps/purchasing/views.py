from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from apps.tenants.permissions import RequiresBranch, IsManagerOrAbove
from .models import Supplier, PurchaseOrder, GoodsReceivedNote
from .serializers import SupplierSerializer, PurchaseOrderSerializer, GoodsReceivedNoteSerializer

class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticated, IsManagerOrAbove]

class PurchaseOrderViewSet(viewsets.ModelViewSet):
    queryset = PurchaseOrder.objects.all()
    serializer_class = PurchaseOrderSerializer
    permission_classes = [IsAuthenticated, RequiresBranch, IsManagerOrAbove]

class GoodsReceivedNoteViewSet(viewsets.ModelViewSet):
    queryset = GoodsReceivedNote.objects.all()
    serializer_class = GoodsReceivedNoteSerializer
    permission_classes = [IsAuthenticated, RequiresBranch, IsManagerOrAbove]
