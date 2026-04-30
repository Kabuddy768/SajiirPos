from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
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
        from workers.mpesa_callbacks import process_mpesa_callback
        schema_name = getattr(request.tenant, 'schema_name', 'public') if hasattr(request, 'tenant') else 'public'
        process_mpesa_callback.delay(request.data, schema_name)
        return Response({'status': 'received'})
