from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from apps.tenants.permissions import get_user_role
from apps.tenants.models import TenantUser

@login_required
def dashboard(request):
    if request.tenant.schema_name == 'public':
        return redirect('/admin/')
    
    role = get_user_role(request)
    if role not in [TenantUser.ROLE_OWNER, TenantUser.ROLE_ADMIN, TenantUser.ROLE_MANAGER]:
        return render(request, 'pos/checkout.html', {'error': 'Unauthorized for dashboard'})
        
    return render(request, 'reports/dashboard.html')
