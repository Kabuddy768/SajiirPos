from rest_framework import viewsets, permissions, response
from rest_framework.decorators import action
from .services import AuditService
from apps.tenants.permissions import IsManagerOrAbove

class AuditViewSet(viewsets.ViewSet):
    """
    ViewSet for audit and anomaly detection metrics.
    """
    permission_classes = [permissions.IsAuthenticated, IsManagerOrAbove]

    @action(detail=False, methods=['get'], url_path='cashier-metrics')
    def cashier_metrics(self, request):
        days = request.query_params.get('days', 30)
        try:
            days = int(days)
        except ValueError:
            days = 30
            
        # Get metrics (filter by branch if user is branch manager)
        branch = None
        # In a real multi-tenant app, request.tenant might restrict this
        # If the user has a specific branch in their profile, we could filter by it
        
        metrics = AuditService.get_cashier_metrics(branch=branch, days=days)
        return response.Response(metrics)
