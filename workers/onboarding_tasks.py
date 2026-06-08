"""
Onboarding Celery Tasks — Tenant Schema Provisioning
======================================================

This task is dispatched asynchronously after a user completes the workspace
setup wizard. It handles:
  1. Creating the Tenant model + PostgreSQL schema (django-tenants auto-migrates)
  2. Binding the subdomain as a Domain record
  3. Linking the owner user to the new tenant
  4. Seeding the schema with default data (expense categories, units)
  5. Activating the tenant so the pending page knows it's ready

This is deliberately async because schema creation + migrations can take
10-20 seconds and must never block an HTTP request.
"""
import logging
from celery import shared_task

logger = logging.getLogger(__name__)

# Subdomains that M-Pesa or your own infrastructure uses as base URLs.
# The onboarding form already validates against this list, but we double-check here.
RESERVED_SUBDOMAINS = {
    'www', 'api', 'admin', 'billing', 'support', 'portal', 'mail',
    'ftp', 'ssh', 'test', 'staging', 'demo', 'app', 'dashboard',
    'static', 'media', 'cdn', 'login', 'sajiirpos', 'sajiir',
}


@shared_task(bind=True, max_retries=3, default_retry_delay=15)
def provision_tenant_schema(self, tenant_name, subdomain, owner_user_id, plan_name):
    """
    Provision a new tenant workspace end-to-end.

    Args:
        tenant_name  (str): Human-readable business name, e.g. "Karen Supermarket"
        subdomain    (str): URL-safe slug, e.g. "karensupermarket"
        owner_user_id (int): PK of the CustomUser to assign as owner
        plan_name    (str): One of: 'starter', 'pro', 'enterprise'
    """
    from django.contrib.auth import get_user_model
    from apps.tenants.models import Tenant, Domain, TenantUser

    User = get_user_model()

    # Safety gate: refuse reserved names even if form validation was bypassed
    if subdomain.lower() in RESERVED_SUBDOMAINS:
        logger.error(
            "provision_tenant_schema: Rejected reserved subdomain '%s' for user %s",
            subdomain, owner_user_id
        )
        return {'status': 'failed', 'reason': 'reserved_subdomain'}

    # Idempotency: if tenant already exists and is active, bail out cleanly
    existing = Tenant.objects.filter(schema_name=subdomain).first()
    if existing and existing.is_active:
        logger.warning(
            "provision_tenant_schema: Tenant '%s' already active. Skipping.", subdomain
        )
        return {'status': 'already_exists'}

    try:
        # ── 1. Create Tenant (django-tenants auto-runs schema migrations) ──────
        if not existing:
            logger.info("Provisioning new schema: %s (plan: %s)", subdomain, plan_name)
            tenant = Tenant.objects.create(
                name=tenant_name,
                schema_name=subdomain.lower(),
                plan=plan_name,
                is_active=False,  # Held inactive until fully provisioned
            )
        else:
            tenant = existing

        # ── 2. Bind Primary Domain ─────────────────────────────────────────────
        base_domain = f"{subdomain.lower()}.sajiirpos.com"
        Domain.objects.get_or_create(
            domain=base_domain,
            defaults={'tenant': tenant, 'is_primary': True}
        )

        # ── 3. Link Owner in public schema ─────────────────────────────────────
        owner = User.objects.get(pk=owner_user_id)
        TenantUser.objects.get_or_create(
            user=owner,
            tenant=tenant,
            defaults={'role': TenantUser.ROLE_OWNER, 'is_active': True}
        )

        # ── 4. Seed tenant schema with default data ────────────────────────────
        _seed_tenant_defaults(tenant)

        # ── 5. Activate tenant ─────────────────────────────────────────────────
        tenant.is_active = True
        tenant.contact_email = owner.email
        tenant.save(update_fields=['is_active', 'contact_email'])

        logger.info(
            "Tenant '%s' provisioned successfully for user %s", subdomain, owner_user_id
        )
        return {'status': 'ready', 'tenant': subdomain}

    except Exception as exc:
        logger.exception(
            "provision_tenant_schema failed for subdomain='%s' user=%s: %s",
            subdomain, owner_user_id, exc
        )
        # Retry up to 3 times with exponential backoff
        raise self.retry(exc=exc)


def _seed_tenant_defaults(tenant):
    """
    Seed a freshly created tenant schema with sensible defaults.
    Runs inside the tenant's schema context.
    """
    from django_tenants.utils import schema_context

    with schema_context(tenant.schema_name):
        # ── Default Expense Categories ────────────────────────────────────────
        try:
            from apps.expenses.models import ExpenseCategory
            default_categories = [
                'Rent & Utilities',
                'Salaries & Wages',
                'Stock Purchase',
                'Transport & Delivery',
                'Marketing & Advertising',
                'Repairs & Maintenance',
                'Miscellaneous',
            ]
            for name in default_categories:
                ExpenseCategory.objects.get_or_create(name=name)
        except Exception as e:
            logger.warning("Could not seed expense categories: %s", e)

        # ── Default Branch ────────────────────────────────────────────────────
        try:
            from apps.branches.models import Branch
            Branch.objects.get_or_create(
                name='Main Branch',
                defaults={
                    'address': '',
                    'phone': '',
                    'etims_branch_code': 'BR01',
                    'is_active': True,
                }
            )
        except Exception as e:
            logger.warning("Could not seed default branch: %s", e)

        logger.info("Seeded defaults for tenant schema: %s", tenant.schema_name)
