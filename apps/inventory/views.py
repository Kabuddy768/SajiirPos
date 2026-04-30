from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.tenants.permissions import IsCashier
from apps.branches.models import Branch
from apps.products.models import Product, ProductBatch
from .models import StockTransfer
from .serializers import (
    StockTransferSerializer,
    TransferCreateSerializer,
    TransferActionSerializer,
)
from .transfer_service import TransferService, TransferError


class StockTransferViewSet(viewsets.ModelViewSet):
    queryset = StockTransfer.objects.select_related(
        'from_branch', 'to_branch',
        'requested_by', 'approved_by', 'shipped_by', 'received_by',
    ).prefetch_related('items__product').all()
    serializer_class = StockTransferSerializer
    permission_classes = [IsAuthenticated, IsCashier]

    def create(self, request, *args, **kwargs):
        serializer = TransferCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            from_branch = Branch.objects.get(id=data['from_branch_id'])
            to_branch = Branch.objects.get(id=data['to_branch_id'])
        except Branch.DoesNotExist:
            return Response({'error': 'Branch not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Resolve products
        items_data = []
        for item in data['items']:
            try:
                product = Product.objects.get(id=item['product_id'])
            except Product.DoesNotExist:
                return Response(
                    {'error': f"Product {item['product_id']} not found."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            batch = None
            if item.get('batch_id'):
                batch = ProductBatch.objects.filter(id=item['batch_id']).first()

            items_data.append({
                'product': product,
                'quantity': item['quantity'],
                'batch': batch,
            })

        try:
            transfer = TransferService.create(
                from_branch=from_branch,
                to_branch=to_branch,
                items_data=items_data,
                requested_by=request.user,
                notes=data.get('notes', ''),
            )
        except TransferError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            StockTransferSerializer(transfer).data,
            status=status.HTTP_201_CREATED,
        )

    # ------------------------------------------------------------------
    # Lifecycle actions
    # ------------------------------------------------------------------
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        transfer = self.get_object()
        try:
            TransferService.approve(transfer, request.user)
        except TransferError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(StockTransferSerializer(transfer).data)

    @action(detail=True, methods=['post'])
    def ship(self, request, pk=None):
        transfer = self.get_object()
        ser = TransferActionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        quantities = ser.validated_data.get('quantities')
        # Convert string keys to int keys if provided
        shipped_quantities = None
        if quantities:
            shipped_quantities = {int(k): v for k, v in quantities.items()}

        try:
            TransferService.ship(transfer, request.user, shipped_quantities)
        except TransferError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(StockTransferSerializer(transfer).data)

    @action(detail=True, methods=['post'])
    def receive(self, request, pk=None):
        transfer = self.get_object()
        ser = TransferActionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        quantities = ser.validated_data.get('quantities')
        received_quantities = None
        if quantities:
            received_quantities = {int(k): v for k, v in quantities.items()}

        try:
            TransferService.receive(transfer, request.user, received_quantities)
        except TransferError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(StockTransferSerializer(transfer).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        transfer = self.get_object()
        try:
            TransferService.cancel(transfer, request.user)
        except TransferError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(StockTransferSerializer(transfer).data)
