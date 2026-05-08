from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import connection
from apps.sales.models import Sale
from apps.sales.services import SaleService
from apps.products.models import Product
from decimal import Decimal
from apps.customers.models import Customer
from apps.products.models import ProductBatch
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import UserRateThrottle
from apps.tenants.permissions import RequiresBranch, IsCashier
import logging

logger = logging.getLogger(__name__)

class SyncSalesView(APIView):
    permission_classes = [IsAuthenticated, RequiresBranch, IsCashier]
    throttle_classes = [UserRateThrottle]

    def _resolve_manager_override(self, request, sale_data):
        """
        Server-side role check for manager_override.
        Cashiers cannot grant themselves manager privileges by setting
        manager_override=true in the offline payload — role is verified here.
        """
        client_override = sale_data.get('manager_override', False)
        if not client_override:
            return False

        from apps.tenants.models import TenantUser
        try:
            tu = TenantUser.objects.get(user=request.user)
            role = tu.role
        except TenantUser.DoesNotExist:
            return False

        # Only managers and above can approve price overrides
        return role in ('manager', 'owner', 'admin')

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
                # Security Check 1: Session Ownership
                session_id = sale_data.get('session_id')
                from apps.sales.models import CashSession
                session = CashSession.objects.filter(id=session_id, cashier=request.user, status='open').first()
                if not session:
                    raise ValueError("Session mismatch or session is closed.")

                # Security Check 2: Backdating window (max 7 days)
                client_created_at_str = sale_data.get('client_created_at')
                from django.utils import timezone
                import datetime
                client_time = timezone.datetime.fromisoformat(client_created_at_str.replace('Z', '+00:00'))
                if client_time < timezone.now() - datetime.timedelta(days=7):
                    raise ValueError("Sale date is too far in the past. Maximum 7 days for offline sync.")
                if client_time > timezone.now() + datetime.timedelta(minutes=30):
                    raise ValueError("Sale date cannot be in the future.")

                # Security Check 3: Server-side manager_override role enforcement.
                # Never trust the client payload for privilege escalation.
                manager_override = self._resolve_manager_override(request, sale_data)

                # Reconstruct cart for SaleService
                cart_payload = sale_data.get('cart', [])
                cart = []
                for item in cart_payload:
                    product = Product.objects.get(id=item['product_id'])
                    
                    # Batch lookup
                    batch = None
                    batch_id = item.get('batch_id')
                    if batch_id:
                        batch = ProductBatch.objects.filter(id=batch_id).first()

                    cart.append({
                        'product': product,
                        'quantity': Decimal(str(item['quantity'])),
                        'unit_price': Decimal(str(item['unit_price'])),
                        'discount_amount': Decimal(str(item.get('discount_amount', '0.0'))),
                        'batch': batch
                    })
                
                # Customer lookup
                customer = None
                customer_id = sale_data.get('customer_id')
                if customer_id:
                    customer = Customer.objects.filter(id=customer_id).first()

                sale = SaleService.complete(
                    cart=cart,
                    session_id=session_id,
                    payments=sale_data.get('payments', []),
                    cashier=request.user,
                    customer=customer,
                    client_created_at=client_created_at_str,
                    offline_uuid=offline_uuid,
                    schema_name=schema_name,
                    manager_override=manager_override
                )

                results.append({
                    'offline_uuid': offline_uuid,
                    'status': 'synced',
                    'sale_number': sale.sale_number
                })
            except Exception as e:
                # Log the full traceback — silent losses are unacceptable
                logger.exception(
                    "Offline sync failed for uuid=%s user=%s",
                    offline_uuid,
                    request.user.email
                )
                results.append({
                    'offline_uuid': offline_uuid,
                    'status': 'failed',
                    'error': str(e)
                })
        
        return Response({'results': results})

