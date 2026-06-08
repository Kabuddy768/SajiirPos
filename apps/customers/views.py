from django.shortcuts import get_object_or_404
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from apps.tenants.permissions import IsCashier
from .models import Customer
from .serializers import CustomerSerializer
from rest_framework.response import Response

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.filter(is_active=True)
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated, IsCashier]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'phone', 'email']

    def get_queryset(self):
        # Allow seeing deleted customers if 'include_inactive' is passed
        if self.request.query_params.get('include_inactive') == 'true':
            return Customer.objects.all()
        return Customer.objects.filter(is_active=True)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        # Need to use all() to find inactive ones
        instance = get_object_or_404(Customer.objects.all(), pk=pk)
        instance.is_active = True
        instance.save()
        return Response(CustomerSerializer(instance).data)
