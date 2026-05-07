from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, get_user_model
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages

from apps.tenants.permissions import get_user_role
from apps.tenants.models import TenantUser
from apps.branches.models import StaffProfile
from .models import StaffInvitation
from .forms import InviteStaffForm, AcceptInvitationForm
from .email import send_invitation_email

User = get_user_model()


@login_required
def invite_send(request):
    """
    Owner/Admin-only view to send a staff invitation.
    GET  → show invite form
    POST → create StaffInvitation + send email
    """
    role = get_user_role(request)
    if role not in ['owner', 'admin']:
        messages.error(request, 'You do not have permission to invite staff.')
        return redirect('dashboard')

    # Tier check: can we add more staff?
    from apps.tenants.tier_limits import can_add_staff
    tenant = getattr(request, 'tenant', None)
    if tenant and not can_add_staff(tenant):
        messages.error(
            request,
            'You have reached the staff limit for your subscription plan. Please upgrade to add more staff.'
        )
        return redirect('dashboard_staff')

    if request.method == 'POST':
        form = InviteStaffForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            invite_role = form.cleaned_data['role']
            branch = form.cleaned_data.get('branch')

            # Prevent duplicate pending invitations for same email/tenant
            existing = StaffInvitation.objects.filter(
                email=email,
                is_used=False,
                expires_at__gt=timezone.now(),
            ).first()
            if existing:
                messages.warning(
                    request,
                    f'A pending invitation for {email} already exists. '
                    f'It expires {existing.expires_at.strftime("%d %b %Y %H:%M")}.'
                )
                return redirect('dashboard_staff')

            invitation = StaffInvitation.objects.create(
                email=email,
                role=invite_role,
                branch=branch,
                invited_by=request.user,
            )

            try:
                send_invitation_email(invitation, request)
                messages.success(request, f'Invitation sent to {email}.')
            except Exception as e:
                messages.error(request, f'Invitation created but email failed: {e}')

            return redirect('dashboard_staff')
    else:
        form = InviteStaffForm()

    return render(request, 'invitations/invite_send.html', {'form': form})


def invite_accept(request):
    """
    Public token-gated view. Anyone with the link can accept.

    GET  ?token=<uuid> → validate token, show form (new user) or redirect to login (existing user)
    POST ?token=<uuid> → create account if new, create TenantUser + StaffProfile, mark token used
    """
    token = request.GET.get('token') or request.POST.get('token')
    if not token:
        return render(request, 'invitations/invite_invalid.html', {
            'reason': 'No invitation token provided.'
        })

    invitation = get_object_or_404(StaffInvitation, token=token)

    if not invitation.is_valid:
        reason = 'This invitation has already been used.' if invitation.is_used else 'This invitation has expired.'
        return render(request, 'invitations/invite_invalid.html', {'reason': reason})

    # Check if the invitee already has an account
    existing_user = User.objects.filter(email=invitation.email).first()

    if request.method == 'POST':
        if existing_user:
            # Existing user — just wire up the TenantUser + StaffProfile
            _create_tenant_membership(invitation, existing_user, request)
            invitation.is_used = True
            invitation.accepted_at = timezone.now()
            invitation.save()
            messages.success(request, f'Welcome back! You have been added as {invitation.get_role_display()}.')
            login(request, existing_user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect(_post_login_url(invitation.role))
        else:
            form = AcceptInvitationForm(request.POST)
            if form.is_valid():
                user = User.objects.create_user(
                    email=invitation.email,
                    password=form.cleaned_data['password'],
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                )
                _create_tenant_membership(invitation, user, request)
                invitation.is_used = True
                invitation.accepted_at = timezone.now()
                invitation.save()
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                messages.success(
                    request,
                    f'Welcome to the team! Your account has been created as {invitation.get_role_display()}.'
                )
                return redirect(_post_login_url(invitation.role))
        # Fall through on form errors:
    else:
        form = AcceptInvitationForm() if not existing_user else None

    return render(request, 'invitations/invite_accept.html', {
        'invitation': invitation,
        'existing_user': existing_user,
        'form': form,
        'token': token,
    })


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _create_tenant_membership(invitation, user, request):
    """Wire up TenantUser (shared DB) and StaffProfile (tenant DB)."""
    tenant = getattr(request, 'tenant', None)
    if tenant:
        TenantUser.objects.get_or_create(
            user=user,
            tenant=tenant,
            defaults={'role': invitation.role},
        )
    if invitation.branch:
        StaffProfile.objects.get_or_create(
            user=user,
            branch=invitation.branch,
            defaults={
                'is_active': True,
                'branch_role': invitation.role,
            },
        )


def _post_login_url(role):
    """Return the appropriate redirect URL for a given role after login."""
    if role in ('owner', 'admin', 'manager'):
        return '/dashboard/'
    elif role == 'auditor':
        return '/dashboard/reports/'
    return '/'  # Cashier → POS till
