"""
eTIMS Celery Task — Background invoice signing
================================================

This task is called after every completed sale to sign the invoice with KRA.
Currently uses a STUB ETIMSClient (see apps/compliance/etims.py).

TODO: Once real KRA eTIMS credentials are obtained, the ETIMSClient stub
will be replaced with actual API calls. This task requires NO changes —
only the ETIMSClient class needs to be updated.
"""

from celery import shared_task
from django_tenants.utils import schema_context
from apps.sales.models import Sale
from apps.compliance.etims import ETIMSClient, ETIMSError

@shared_task(bind=True, max_retries=5, default_retry_delay=30)
def sign_sale_etims(self, sale_id, schema_name):
    with schema_context(schema_name):
        try:
            sale = Sale.objects.get(pk=sale_id)
            ETIMSClient(branch=sale.branch).sign_sale(sale)
        except Sale.DoesNotExist:
            pass
        except Exception as exc: # ETIMSError
            self.retry(exc=exc)

@shared_task
def retry_pending_etims_submissions(schema_name):
    """
    Find sales stuck in 'pending' status for > 5 minutes and retry signing.
    Useful for closing gaps caused by transient Celery or API downtime.
    """
    from django.utils import timezone
    from datetime import timedelta
    with schema_context(schema_name):
        cutoff = timezone.now() - timedelta(minutes=5)
        pending_sales = Sale.objects.filter(
            etims_submission_status='pending',
            created_at__lt=cutoff,
            status='completed' # Don't try to sign voided or draft sales
        )
        for sale in pending_sales:
            sign_sale_etims.delay(sale.id, schema_name)
