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
