from django.utils.deprecation import MiddlewareMixin
from .models import StaffProfile

class BranchMiddleware(MiddlewareMixin):
    """
    Middleware that attaches the current active branch and staff profile to the request.
    This simplifies access to branch-level context across the app.
    
    Access via: request.branch and request.staff_profile
    """
    def process_request(self, request):
        request.branch = None
        request.staff_profile = None

        if request.user.is_authenticated:
            # 1. Try to get branch from session (for users with multiple branch profiles)
            session_branch_id = request.session.get('active_branch_id')
            
            if session_branch_id:
                profile = StaffProfile.objects.filter(
                    user=request.user, 
                    branch_id=session_branch_id,
                    is_active=True
                ).select_related('branch').first()
                if profile:
                    request.branch = profile.branch
                    request.staff_profile = profile
            
            # 2. Fallback: Get the first active profile if no session or session branch not valid
            if not request.staff_profile:
                profile = StaffProfile.objects.filter(
                    user=request.user, 
                    is_active=True
                ).select_related('branch').first()
                
                if profile:
                    request.branch = profile.branch
                    request.staff_profile = profile
                    # Persist in session for consistency
                    request.session['active_branch_id'] = profile.branch_id
