from django.db.models import F
from django_tenants.utils import schema_context
from celery import shared_task
from apps.tenants.models import Tenant
from apps.inventory.models import BranchStock
from apps.audit.models import Notification

@shared_task
def check_inventory_levels():
    """
    Scan all branches for products below their minimum stock level and log alerts.
    """
    for tenant in Tenant.objects.exclude(schema_name='public'):
        with schema_context(tenant.schema_name):
            low_stocks = BranchStock.objects.filter(
                quantity__lte=F('product__minimum_stock_level')
            ).select_related('product', 'branch')
            
            for stock in low_stocks:
                message = f"{stock.product.name} at {stock.branch.name} is current: {stock.quantity}, threshold: {stock.product.minimum_stock_level}"
                print(f"LOW STOCK [{tenant.name}]: {message}")
                Notification.objects.create(
                    type='low_stock',
                    title='Low Stock Alert',
                    message=message,
                    branch=stock.branch
                )
