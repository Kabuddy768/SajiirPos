from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from apps.tenants.permissions import IsCashier
from .models import Customer
from .serializers import CustomerSerializer
from rest_framework import filters, status
from rest_framework.response import Response

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.filter(is_active=True)
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated, IsCashier]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'phone', 'email']

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
