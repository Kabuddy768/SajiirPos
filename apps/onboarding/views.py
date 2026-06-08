"""
Onboarding Views — Landing page + Self-signup wizard
======================================================
"""
import logging
from django.shortcuts import render, redirect
from django.contrib.auth import login, get_user_model
from django.contrib import messages
from django.http import JsonResponse

from .forms import TenantRegisterForm, WorkspaceSetupForm

logger = logging.getLogger(__name__)
User = get_user_model()


# ─── Landing Page ─────────────────────────────────────────────────────────────

def landing_page(request):
    """
    Public marketing landing page.
    Served at the root domain (www.sajiirpos.com / localhost).
    If a logged-in user hits the root domain they should be redirected
    to their tenant dashboard.
    """
    # If they're already authenticated, redirect to their workspace
    if request.user.is_authenticated:
        return redirect('/dashboard/')

    return render(request, 'onboarding/landing.html', {
        'page_title': 'Sajiir POS — Smart Retail Management for Kenyan Businesses',
    })


# ─── Step 1: Create Account ───────────────────────────────────────────────────

def tenant_register(request):
    """
    Step 1: Collect name, email, password.
    On success → create User in public schema → redirect to Step 2 (workspace setup).
    """
    if request.user.is_authenticated:
        return redirect('/register/workspace/')

    if request.method == 'POST':
        form = TenantRegisterForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data

            # Create the user in the PUBLIC (shared) schema
            user = User.objects.create_user(
                email=d['email'],
                password=d['password'],
                first_name=d['first_name'],
                last_name=d['last_name'],
            )

            # Log them in immediately and proceed to workspace setup
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('tenant_workspace_setup')
    else:
        form = TenantRegisterForm()

    return render(request, 'onboarding/register.html', {
        'form': form,
        'page_title': 'Create your Sajiir POS account',
    })


# ─── Step 2: Workspace + Plan Setup ───────────────────────────────────────────

def tenant_workspace_setup(request):
    """
    Step 2: Select business name, subdomain slug, and subscription plan.
    On valid POST → kick off async Celery task to provision the tenant schema.
    """
    if not request.user.is_authenticated:
        return redirect('tenant_register')

    if request.method == 'POST':
        form = WorkspaceSetupForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data

            # Store provisioning data in session so the pending page can show it
            request.session['pending_workspace'] = {
                'business_name': d['business_name'],
                'subdomain': d['subdomain'],
                'plan': d['plan'],
                'user_id': request.user.id,
            }

            # Dispatch async provisioning task
            try:
                from workers.onboarding_tasks import provision_tenant_schema
                provision_tenant_schema.delay(
                    tenant_name=d['business_name'],
                    subdomain=d['subdomain'],
                    owner_user_id=request.user.id,
                    plan_name=d['plan'],
                )
            except Exception as e:
                logger.exception("Failed to dispatch provision_tenant_schema task: %s", e)
                messages.error(
                    request,
                    'There was a problem starting your workspace setup. '
                    'Please try again or contact support@sajiirpos.com.'
                )
                return render(request, 'onboarding/workspace_setup.html', {
                    'form': form,
                    'page_title': 'Set up your workspace',
                })

            return redirect('tenant_creation_pending')
    else:
        form = WorkspaceSetupForm()

    return render(request, 'onboarding/workspace_setup.html', {
        'form': form,
        'page_title': 'Set up your workspace',
    })


# ─── Pending / Loading Screen ─────────────────────────────────────────────────

def tenant_creation_pending(request):
    """
    Shows a loading animation while the Celery task provisions the tenant schema.
    Polls /register/status/ via JS to know when to redirect.
    """
    workspace_data = request.session.get('pending_workspace', {})
    if not workspace_data:
        return redirect('tenant_register')

    return render(request, 'onboarding/pending.html', {
        'subdomain': workspace_data.get('subdomain', ''),
        'business_name': workspace_data.get('business_name', ''),
        'plan': workspace_data.get('plan', 'starter'),
        'page_title': 'Setting up your workspace…',
    })


# ─── Status Poll API ──────────────────────────────────────────────────────────

def tenant_creation_status(request):
    """
    AJAX endpoint polled by the pending page to check if provisioning is done.
    Returns JSON: { "status": "ready"|"pending"|"failed", "url": "..." }
    """
    workspace_data = request.session.get('pending_workspace', {})
    if not workspace_data:
        return JsonResponse({'status': 'failed', 'message': 'Session expired.'})

    subdomain = workspace_data.get('subdomain', '')

    from apps.tenants.models import Tenant
    try:
        tenant = Tenant.objects.get(schema_name=subdomain)
        if tenant.is_active:
            # Clear session now that workspace is ready
            request.session.pop('pending_workspace', None)
            workspace_url = f"http://{subdomain}.sajiirpos.com/"
            return JsonResponse({'status': 'ready', 'url': workspace_url})
        else:
            return JsonResponse({'status': 'pending'})
    except Tenant.DoesNotExist:
        return JsonResponse({'status': 'pending'})
