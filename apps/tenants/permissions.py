from rest_framework import permissions
from .models import TenantUser

def get_user_role(request):
    if not request.user.is_authenticated:
        return None
    try:
        tenant = request.tenant
        tenant_user = TenantUser.objects.get(user=request.user, tenant=tenant, is_active=True)
        return tenant_user.role
    except (AttributeError, TenantUser.DoesNotExist):
        return None

class IsOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        return get_user_role(request) == TenantUser.ROLE_OWNER

class IsAdminOrAbove(permissions.BasePermission):
    def has_permission(self, request, view):
        role = get_user_role(request)
        return role in [TenantUser.ROLE_OWNER, TenantUser.ROLE_ADMIN]

class IsManagerOrAbove(permissions.BasePermission):
    def has_permission(self, request, view):
        role = get_user_role(request)
        return role in [TenantUser.ROLE_OWNER, TenantUser.ROLE_ADMIN, TenantUser.ROLE_MANAGER]

class IsCashier(permissions.BasePermission):
    def has_permission(self, request, view):
        role = get_user_role(request)
        return role in [TenantUser.ROLE_OWNER, TenantUser.ROLE_ADMIN, TenantUser.ROLE_MANAGER, TenantUser.ROLE_CASHIER]

class IsAuditor(permissions.BasePermission):
    def has_permission(self, request, view):
        role = get_user_role(request)
        return role in [TenantUser.ROLE_OWNER, TenantUser.ROLE_ADMIN, TenantUser.ROLE_AUDITOR]

class RequiresBranch(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
            
        try:
            tenant = request.tenant
            tenant_user = TenantUser.objects.get(user=request.user, tenant=tenant, is_active=True)
        except (AttributeError, TenantUser.DoesNotExist):
            return False
            
        if tenant_user.branch is None:
            return True
            
        requested_branch_id = request.data.get('branch') or request.query_params.get('branch')
        if not requested_branch_id:
            return False
            
        return str(tenant_user.branch.id) == str(requested_branch_id)
