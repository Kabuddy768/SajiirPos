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
        
        client = MpesaClient(tenant=getattr(request, 'tenant', None))
        response = client.initiate_stk_push(phone, amount, reference)
        return Response(response)

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
