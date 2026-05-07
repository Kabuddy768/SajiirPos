"""
Post-login redirect helpers — called after login to route user to correct dashboard.
Set LOGIN_REDIRECT_URL = 'post_login_redirect' in settings.
"""
from apps.tenants.permissions import get_user_role


def get_post_login_url(request):
    """Return the URL to redirect to after a successful login based on role."""
    role = get_user_role(request)
    if role in ('owner', 'admin', 'manager'):
        return '/dashboard/'
    elif role == 'auditor':
        return '/dashboard/reports/'
    return '/'  # Cashier → POS till screen
