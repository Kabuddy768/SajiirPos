from django.db.models import F
from django_tenants.utils import schema_context
from celery import shared_task
from apps.tenants.models import Tenant
from apps.inventory.models import BranchStock

@shared_task
def check_inventory_levels():
    """
    Scan all branches for products below their minimum stock level and log alerts.
    """
    for tenant in Tenant.objects.exclude(schema_name='public'):
        with schema_context(tenant.schema_name):
            # Find stocks where current quantity is less than or equal to minimum_stock_level
            low_stocks = BranchStock.objects.filter(
                quantity__lte=F('product__minimum_stock_level')
            ).select_related('product', 'branch')
            
            for stock in low_stocks:
                # Alert threshold could be configured globally or per product.
                # Here we use product.minimum_stock_level.
                print(f"LOW STOCK [{tenant.name}]: {stock.product.name} at {stock.branch.name} "
                      f"is current: {stock.quantity}, threshold: {stock.product.minimum_stock_level}")
