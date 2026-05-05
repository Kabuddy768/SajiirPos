from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.cache import cache
from .models import Sale, CashSession
from .serializers import SaleSerializer, SaleCreateSerializer, CashSessionSerializer, ProductSerializer
from apps.products.models import Product
from .services import SaleService

from rest_framework.permissions import IsAuthenticated
from apps.tenants.permissions import IsCashier
from apps.customers.models import Customer

class SaleViewSet(viewsets.ModelViewSet):
    queryset = Sale.objects.all()
    serializer_class = SaleSerializer
    permission_classes = [IsAuthenticated, IsCashier]

    def create(self, request, *args, **kwargs):
        serializer = SaleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        customer = None
        if data.get('customer_id'):
            try:
                customer = Customer.objects.get(id=data['customer_id'])
            except Customer.DoesNotExist:
                pass

        cart = []
        for item in data['cart']:
            try:
                product = Product.objects.get(id=item['product_id'])
                cart_item = dict(item)
                cart_item['product'] = product
                cart_item['batch'] = None  # Simplification for now
                cart.append(cart_item)
            except Product.DoesNotExist:
                return Response({'error': f"Product {item['product_id']} not found"}, status=status.HTTP_400_BAD_REQUEST)
        
        has_mpesa = any(p['method'] == 'mpesa' for p in data['payments'])
        if has_mpesa:
            cache_key = f"pending_sale_{data['offline_uuid']}"
            cache.set(cache_key, {
                'cart': data['cart'],
                'session_id': data['session_id'],
                'payments': data['payments'],
                'cashier_id': request.user.id,
                'customer_id': data.get('customer_id'),
                'client_created_at': data['client_created_at'],
                'offline_uuid': data['offline_uuid'],
                'manager_override': data.get('manager_override', False)
            }, timeout=600)
            
            mpesa_payment = next(p for p in data['payments'] if p['method'] == 'mpesa')
            from apps.payments.mpesa import MpesaClient
            client = MpesaClient(tenant=getattr(request, 'tenant', None))
            response = client.initiate_stk_push(
                phone_number=mpesa_payment.get('mpesa_phone', ''),
                amount=mpesa_payment['amount'],
                reference=str(data['offline_uuid'])
            )
            
            checkout_id = response.get('CheckoutRequestID')
            if checkout_id:
                cache.set(f"mpesa_checkout_{checkout_id}", data['offline_uuid'], timeout=600)

            return Response({'status': 'pending_mpesa', 'mpesa_response': response}, status=status.HTTP_202_ACCEPTED)

        try:
            sale = SaleService.complete(
                cart=cart,
                session_id=data['session_id'],
                payments=data['payments'],
                cashier=request.user,
                customer=customer, 
                client_created_at=data['client_created_at'],
                offline_uuid=data['offline_uuid'],
                schema_name=getattr(request.tenant, 'schema_name', 'public') if hasattr(request, 'tenant') else 'public',
                manager_override=data.get('manager_override', False)
            )
            return Response(SaleSerializer(sale).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def void(self, request, pk=None):
        sale = self.get_object()
        reason = request.data.get('reason', '')
        try:
            SaleService.void(sale, voided_by=request.user, reason=reason)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(SaleSerializer(sale).data)

    @action(detail=True, methods=['get'])
    def receipt(self, request, pk=None):
        sale = self.get_object()
        
        receipt_text = f"=== {sale.branch.name} ===\n"
        receipt_text += f"Sale #: {sale.sale_number}\n"
        receipt_text += f"Date: {sale.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        receipt_text += f"Cashier: {sale.cashier.username}\n"
        receipt_text += "--------------------------\n"
        
        for item in sale.items.all():
            receipt_text += f"{item.product.name[:15]:<15} {item.quantity} x {item.unit_price}\n"
            receipt_text += f"Total: {item.line_total:>20}\n"
            
        receipt_text += "--------------------------\n"
        receipt_text += f"Subtotal: {sale.subtotal:>16}\n"
        receipt_text += f"Tax: {sale.tax_amount:>21}\n"
        receipt_text += f"TOTAL: {sale.total_amount:>19}\n"
        receipt_text += "==========================\n"
        
        return Response({
            'text': receipt_text,
            'sale_id': sale.id,
            'sale_number': sale.sale_number
        })

class ProductLookupViewSet(viewsets.GenericViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated, IsCashier]

    @action(detail=False, methods=['get'])
    def by_barcode(self, request):
        barcode = request.query_params.get('barcode')
        try:
            product = Product.objects.get(barcode=barcode)
            return Response([ProductSerializer(product).data]) # Return as list
        except Product.DoesNotExist:
            return Response([], status=status.HTTP_404_NOT_FOUND) # Return empty list

class CashSessionViewSet(viewsets.ModelViewSet):
    queryset = CashSession.objects.all()
    serializer_class = CashSessionSerializer
    permission_classes = [IsAuthenticated, IsCashier]
