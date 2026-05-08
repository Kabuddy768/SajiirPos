from rest_framework import viewsets, status
from rest_framework.response import Response
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

    def create(self, request, *args, **kwargs):
        """Override to surface margin warnings from GRNService.receive()."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        grn = serializer.save()

        warnings = getattr(grn, '_receive_warnings', [])
        data = serializer.data
        if warnings:
            data = dict(data)
            data['warnings'] = warnings

        headers = self.get_success_headers(serializer.data)
        return Response(data, status=status.HTTP_201_CREATED, headers=headers)
