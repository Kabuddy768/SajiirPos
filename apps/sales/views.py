from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.cache import cache
from .models import Sale, CashSession
from .serializers import SaleSerializer, SaleCreateSerializer, CashSessionSerializer, ProductSerializer
from apps.products.models import Product
from .services import SaleService

class SaleViewSet(viewsets.ModelViewSet):
    queryset = Sale.objects.all()
    serializer_class = SaleSerializer

    def create(self, request, *args, **kwargs):
        serializer = SaleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
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
                'client_created_at': data['client_created_at'],
                'offline_uuid': data['offline_uuid']
            }, timeout=600)
            
            mpesa_payment = next(p for p in data['payments'] if p['method'] == 'mpesa')
            from apps.payments.mpesa import MpesaClient
            client = MpesaClient(tenant=getattr(request, 'tenant', None))
            response = client.initiate_stk_push(
                phone_number=mpesa_payment.get('mpesa_phone', ''),
                amount=mpesa_payment['amount'],
                reference=str(data['offline_uuid'])
            )
            return Response({'status': 'pending_mpesa', 'mpesa_response': response}, status=status.HTTP_202_ACCEPTED)

        try:
            sale = SaleService.complete(
                cart=cart,
                session_id=data['session_id'],
                payments=data['payments'],
                cashier=request.user,
                customer=None, 
                client_created_at=data['client_created_at'],
                offline_uuid=data['offline_uuid'],
                schema_name=getattr(request.tenant, 'schema_name', 'public') if hasattr(request, 'tenant') else 'public'
            )
            return Response(SaleSerializer(sale).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ProductLookupViewSet(viewsets.GenericViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    @action(detail=False, methods=['get'])
    def by_barcode(self, request):
        barcode = request.query_params.get('barcode')
        try:
            product = Product.objects.get(barcode=barcode)
            return Response(ProductSerializer(product).data)
        except Product.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

class CashSessionViewSet(viewsets.ModelViewSet):
    queryset = CashSession.objects.all()
    serializer_class = CashSessionSerializer
