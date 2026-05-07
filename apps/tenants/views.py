from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from apps.tenants.permissions import get_user_role
from apps.tenants.models import TenantUser
from apps.tenants.tier_limits import get_limits
from apps.branches.models import Branch

@login_required
def subscription_page(request):
    role = get_user_role(request)
    if role != TenantUser.ROLE_OWNER:
        return redirect('dashboard')

    tenant = request.tenant
    limits = get_limits(tenant)
    
    # Usage metrics
    branch_count = Branch.objects.filter(is_active=True).count()
    staff_count = TenantUser.objects.filter(tenant=tenant, is_active=True).count()

    usage = {
        'branches': {
            'current': branch_count,
            'limit': limits['branches'],
            'percent': min(100, (branch_count / limits['branches'] * 100)) if limits['branches'] > 0 else 100
        },
        'staff': {
            'current': staff_count,
            'limit': limits['staff'],
            'percent': min(100, (staff_count / limits['staff'] * 100)) if limits['staff'] > 0 else 100
        }
    }

    return render(request, 'tenants/subscription.html', {
        'tenant': tenant,
        'limits': limits,
        'usage': usage,
        'user_role': role,
    })
