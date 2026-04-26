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
        # M-Pesa callback processor
        # In a real app, this parses Daraja callback, gets the offline_uuid from cache,
        # and calls SaleService.complete()
        return Response({'status': 'success'})
