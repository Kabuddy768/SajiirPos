from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.conf import settings
import hmac
import hashlib
from .models import Payment
from .mpesa import MpesaClient

class MpesaViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['post'])
    def initiate(self, request):
        phone = request.data.get('phone')
        amount = request.data.get('amount')
        reference = request.data.get('reference')
        
        # Get active session for this cashier to determine the branch
        from apps.sales.models import CashSession
        session = CashSession.objects.filter(cashier=request.user, status='open').first()
        branch = session.branch if session else None
        
        client = MpesaClient(tenant=getattr(request, 'tenant', None), branch=branch)
        response = client.initiate_stk_push(phone, amount, reference)
        return Response(response)

    @action(detail=False, methods=['post'])
    def query(self, request):
        """Check if an STK push payment was completed by querying Safaricom directly."""
        checkout_request_id = request.data.get('checkout_request_id')
        if not checkout_request_id:
            return Response({'error': 'checkout_request_id required'}, status=400)

        # Get active session for this cashier to determine the branch
        from apps.sales.models import CashSession
        session = CashSession.objects.filter(cashier=request.user, status='open').first()
        branch = session.branch if session else None

        client = MpesaClient(tenant=getattr(request, 'tenant', None), branch=branch)
        result = client.query_stk_status(checkout_request_id)

        # ResultCode 0 = paid, 1032 = cancelled by user, 1037 = timeout
        result_code = result.get('ResultCode')
        if result_code is not None:
            result_code = int(result_code)

        return Response({
            'paid': result_code == 0,
            'cancelled': result_code == 1032,
            'result_code': result_code,
            'result_desc': result.get('ResultDesc', ''),
        })

    @action(detail=False, methods=['post'])
    def callback(self, request):
        secret = getattr(settings, 'MPESA_CALLBACK_SECRET', None)
        if secret:
            signature = request.headers.get('X-Mpesa-Signature', '')
            expected_signature = hmac.new(
                secret.encode('utf-8'),
                request.body,
                hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(signature, expected_signature):
                raise PermissionDenied("Invalid HMAC signature")


        from workers.mpesa_callbacks import process_mpesa_callback
        schema_name = getattr(request.tenant, 'schema_name', 'public') if hasattr(request, 'tenant') else 'public'
        process_mpesa_callback.delay(request.data, schema_name)
        return Response({'status': 'received'})
