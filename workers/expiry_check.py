from datetime import timedelta
from django.utils import timezone
from django_tenants.utils import schema_context
from celery import shared_task
from apps.tenants.models import Tenant
from apps.products.models import ProductBatch

@shared_task
def check_expiry_dates():
    """
    Scan all batches for nearing expiry dates and log alerts.
    """
    for tenant in Tenant.objects.exclude(schema_name='public'):
        with schema_context(tenant.schema_name):
            today = timezone.localtime().date()
            # Find batches expiring soon based on product-specific alert days
            # If product.expiry_alert_days is 30, alert if expiry_date <= today + 30
            batches = ProductBatch.objects.filter(
                expiry_date__lte=today + timedelta(days=90), # Broad scan
                quantity_remaining__gt=0,
                is_written_off=False
            ).select_related('product')
            
            for batch in batches:
                alert_threshold = today + timedelta(days=batch.product.expiry_alert_days)
                if batch.expiry_date <= alert_threshold:
                    # In a production app, we would create a Notification model instance
                    # or send an email/SMS alert to the manager.
                    print(f"EXPIRY ALERT [{tenant.name}]: {batch.product.name} (Batch: {batch.batch_number}) "
                          f"expires on {batch.expiry_date}")
