from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import connection
from apps.sales.models import Sale
from apps.sales.services import SaleService
from apps.products.models import Product
from decimal import Decimal

class SyncSalesView(APIView):
    def post(self, request, *args, **kwargs):
        payload = request.data
        sales_data = payload.get('sales', [])
        
        results = []
        schema_name = connection.schema_name
        
        for sale_data in sales_data:
            offline_uuid = sale_data.get('offline_uuid')
            # Check existing explicitly just to be safe
            if Sale.objects.filter(offline_uuid=offline_uuid).exists():
                results.append({
                    'offline_uuid': offline_uuid,
                    'status': 'already_synced'
                })
                continue
                
            try:
                # Reconstruct cart for SaleService
                cart_payload = sale_data.get('cart', [])
                cart = []
                for item in cart_payload:
                    product = Product.objects.get(id=item['product_id'])
                    cart.append({
                        'product': product,
                        'quantity': Decimal(str(item['quantity'])),
                        'unit_price': Decimal(str(item['unit_price'])),
                        'discount_amount': Decimal(str(item.get('discount_amount', '0.0'))),
                        'batch': None # Lookup actual batch model if passed
                    })
                
                # Assume simpler passed structures for others for demo
                sale = SaleService.complete(
                    cart=cart,
                    session_id=sale_data.get('session_id'),
                    payments=sale_data.get('payments', []),
                    cashier=request.user,
                    customer=None, # Needs lookup
                    client_created_at=sale_data.get('client_created_at'),
                    offline_uuid=offline_uuid,
                    schema_name=schema_name
                )
                
                results.append({
                    'offline_uuid': offline_uuid,
                    'status': 'synced',
                    'sale_number': sale.sale_number
                })
            except Exception as e:
                # In real scenario: log it, maybe return failure
                results.append({
                    'offline_uuid': offline_uuid,
                    'status': 'failed',
                    'error': str(e)
                })
        
        return Response({'results': results})
