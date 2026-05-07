"""
Tier limits for Sajiir POS subscription plans.

Usage:
    from apps.tenants.tier_limits import can_add_branch, can_add_staff

    if not can_add_branch(tenant):
        return 403 with upgrade prompt
"""
from apps.tenants.models import TenantUser

TIER_LIMITS = {
    'starter': {
        'branches': 1,
        'staff': 5,
        'etims': False,
        'transfers': False,
        'sales_reports_days': 30,
        'inventory_reports': 'basic',
        'whatsapp_receipts': False,
        'loyalty': False,
    },
    'pro': {
        'branches': 3,
        'staff': 15,
        'etims': True,
        'transfers': True,
        'sales_reports_days': 365,
        'inventory_reports': 'full',
        'whatsapp_receipts': True,
        'loyalty': True,
    },
    'enterprise': {
        'branches': 9999,
        'staff': 9999,
        'etims': True,
        'transfers': True,
        'sales_reports_days': 9999,
        'inventory_reports': 'full_export',
        'whatsapp_receipts': True,
        'loyalty': True,
    },
}


def get_limits(tenant):
    """Return the limit dict for the tenant's current plan."""
    plan = (getattr(tenant, 'plan', None) or 'starter').lower()
    return TIER_LIMITS.get(plan, TIER_LIMITS['starter'])


def can_add_branch(tenant):
    """Return True if tenant can create another branch within their plan."""
    from apps.branches.models import Branch
    limit = get_limits(tenant)['branches']
    current = Branch.objects.filter(is_active=True).count()
    return current < limit


def can_add_staff(tenant):
    """Return True if tenant can invite another staff member within their plan."""
    limit = get_limits(tenant)['staff']
    current = TenantUser.objects.filter(tenant=tenant, is_active=True).count()
    return current < limit


def has_etims(tenant):
    """Return True if tenant's plan includes eTIMS integration."""
    return get_limits(tenant)['etims']


def has_stock_transfers(tenant):
    """Return True if tenant's plan includes stock transfers."""
    return get_limits(tenant)['transfers']


def has_whatsapp_receipts(tenant):
    """Return True if tenant's plan includes WhatsApp receipts."""
    return get_limits(tenant)['whatsapp_receipts']
