from rest_framework import permissions
from .models import TenantUser

def get_user_role(request):
    """
    Get the effective role of the user for the current request context.
    Uses BranchMiddleware's request.staff_profile for branch-level overrides.
    """
    if not request.user.is_authenticated:
        return None
    
    try:
        # 1. Get the ceiling role from the tenant level
        from .models import TenantUser
        tenant_user = TenantUser.objects.get(user=request.user, tenant=request.tenant, is_active=True)
        tenant_role = tenant_user.role

        # Owners and Admins have their tenant role everywhere
        if tenant_role in [TenantUser.ROLE_OWNER, TenantUser.ROLE_ADMIN]:
            return tenant_role

        # 2. Check for branch-level override from middleware
        staff_profile = getattr(request, 'staff_profile', None)
        if staff_profile and staff_profile.is_active:
            role_hierarchy = {
                TenantUser.ROLE_OWNER: 5,
                TenantUser.ROLE_ADMIN: 4,
                TenantUser.ROLE_MANAGER: 3,
                TenantUser.ROLE_AUDITOR: 2,
                TenantUser.ROLE_CASHIER: 1
            }
            branch_role_level = role_hierarchy.get(staff_profile.branch_role, 0)
            tenant_role_level = role_hierarchy.get(tenant_role, 0)
            
            # Branch role cannot exceed the TenantUser ceiling
            return staff_profile.branch_role if branch_role_level <= tenant_role_level else tenant_role
        
        return tenant_role
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
    """
    Ensures the user has an active branch context.
    If a specific branch is requested via ?branch=ID, verifies user belongs to it.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
            
        # Middleware should have populated request.branch
        if not getattr(request, 'branch', None):
            return False
            
        role = get_user_role(request)
        if role in [TenantUser.ROLE_OWNER, TenantUser.ROLE_ADMIN]:
            return True
            
        # Verify requested branch matches active branch context
        requested_branch_id = None
        if request.method in permissions.SAFE_METHODS:
            requested_branch_id = request.query_params.get('branch')
        else:
            requested_branch_id = (request.data.get('branch') if hasattr(request, 'data') else None) or request.query_params.get('branch')
            
        if requested_branch_id:
            return str(request.branch.id) == str(requested_branch_id)
        return True

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
            
        role = get_user_role(request)
        if role in [TenantUser.ROLE_OWNER, TenantUser.ROLE_ADMIN]:
            return True
            
        # If the object has a branch attribute, it must match the active branch
        if hasattr(obj, 'branch'):
            return obj.branch == request.branch
        return True
