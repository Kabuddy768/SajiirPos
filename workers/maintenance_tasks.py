"""
Periodic maintenance tasks for Sajiir POS.
These run cross-tenant and target the public schema unless schema_name is passed.
"""
from celery import shared_task
from django.utils import timezone
import datetime
import logging

logger = logging.getLogger(__name__)


@shared_task
def cleanup_daily_sale_counters(retention_days=90):
    """
    Delete DailySaleCounter rows older than retention_days (default 90).
    The counter is only needed for same-day uniqueness; old rows accumulate forever
    without this cleanup.

    Called from Celery Beat — no schema_name needed because DailySaleCounter
    rows exist per-tenant schema; this task must be invoked per tenant.
    To call for all tenants, iterate Client.objects.all() in a management command.
    """
    from apps.tenants.models import Tenant
    from django_tenants.utils import schema_context

    cutoff = timezone.now().date() - datetime.timedelta(days=retention_days)
    cutoff_str = cutoff.strftime('%Y%m%d')
    total_deleted = 0

    for client in Tenant.objects.exclude(schema_name='public'):
        with schema_context(client.schema_name):
            from apps.sales.models import DailySaleCounter
            deleted, _ = DailySaleCounter.objects.filter(date_str__lt=cutoff_str).delete()
            if deleted:
                logger.info(
                    "cleanup_daily_sale_counters: deleted %d rows older than %s in schema %s",
                    deleted, cutoff_str, client.schema_name
                )
            total_deleted += deleted

    return total_deleted


@shared_task
def dispatch_daily_tenant_tasks():
    """
    Master task to dispatch daily per-tenant background jobs.
    Iterates through all clients and calls their specific tasks with schema context.
    """
    from apps.tenants.models import Tenant
    from workers.loyalty_tasks import detect_churned_customers
    from workers.purchasing_tasks import generate_demand_based_po
    
    clients = Tenant.objects.exclude(schema_name='public')
    for client in clients:
        # Dispatch churn detection
        detect_churned_customers.delay(schema_name=client.schema_name)
        # Dispatch demand-based PO generation
        generate_demand_based_po.delay(schema_name=client.schema_name)
    
    return f"Dispatched tasks for {clients.count()} tenants."
@shared_task
def dispatch_hourly_etims_retry():
    """
    Dispatch eTIMS retry tasks for all tenants every hour.
    Ensures near-real-time compliance even if initial signing fails.
    """
    from apps.tenants.models import Tenant
    from workers.etims_tasks import retry_pending_etims_submissions
    
    clients = Tenant.objects.exclude(schema_name='public')
    for client in clients:
        retry_pending_etims_submissions.delay(schema_name=client.schema_name)
    
    return f"Dispatched eTIMS retries for {clients.count()} tenants."
