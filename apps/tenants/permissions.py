from rest_framework import permissions
from .models import TenantUser

def get_user_role(request):
    if not request.user.is_authenticated:
        return None
    try:
        tenant = request.tenant
        tenant_user = TenantUser.objects.get(user=request.user, tenant=tenant, is_active=True)
        tenant_role = tenant_user.role

        if tenant_role in [TenantUser.ROLE_OWNER, TenantUser.ROLE_ADMIN]:
            return tenant_role

        requested_branch_id = None
        if hasattr(request, 'query_params'):
            if request.method in permissions.SAFE_METHODS:
                requested_branch_id = request.query_params.get('branch')
            else:
                requested_branch_id = request.data.get('branch') if hasattr(request, 'data') else None
                if not requested_branch_id:
                    requested_branch_id = request.query_params.get('branch')
        
        if requested_branch_id:
            from apps.branches.models import StaffProfile
            try:
                profile = StaffProfile.objects.filter(user=request.user, branch_id=requested_branch_id, is_active=True).first()
                if profile and hasattr(profile, 'branch_role'):
                    role_hierarchy = {
                        TenantUser.ROLE_OWNER: 5,
                        TenantUser.ROLE_ADMIN: 4,
                        TenantUser.ROLE_MANAGER: 3,
                        TenantUser.ROLE_AUDITOR: 2,
                        TenantUser.ROLE_CASHIER: 1
                    }
                    branch_role_level = role_hierarchy.get(profile.branch_role, 0)
                    tenant_role_level = role_hierarchy.get(tenant_role, 0)
                    return profile.branch_role if branch_role_level <= tenant_role_level else tenant_role
            except Exception:
                pass
                
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
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
            
        role = get_user_role(request)
        if role in [TenantUser.ROLE_OWNER, TenantUser.ROLE_ADMIN]:
            return True
            
        from apps.branches.models import StaffProfile
        # Use filter().first() not .get() — a user can have multiple StaffProfile
        # rows in a multi-branch environment; .get() raises MultipleObjectsReturned.
        profile = StaffProfile.objects.filter(user=request.user, is_active=True).first()
        if not profile:
            return False
        user_branch = profile.branch
            
        if request.method in permissions.SAFE_METHODS:
            requested_branch_id = request.query_params.get('branch')
        else:
            requested_branch_id = request.data.get('branch') or request.query_params.get('branch')
            
        if requested_branch_id:
            return str(user_branch.id) == str(requested_branch_id)
        return True

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
            
        role = get_user_role(request)
        if role in [TenantUser.ROLE_OWNER, TenantUser.ROLE_ADMIN]:
            return True
            
        from apps.branches.models import StaffProfile
        profile = StaffProfile.objects.filter(user=request.user, is_active=True).first()
        if not profile:
            return False
        user_branch = profile.branch
            
        if hasattr(obj, 'branch'):
            return str(user_branch.id) == str(obj.branch.id)
        return False
