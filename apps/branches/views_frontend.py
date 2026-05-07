from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.tenants.permissions import get_user_role
from apps.tenants.models import TenantUser
from .models import Branch
from .forms import BranchForm

@login_required
def branch_list(request):
    role = get_user_role(request)
    if role not in [TenantUser.ROLE_OWNER, TenantUser.ROLE_ADMIN]:
        return redirect('dashboard')

    branches = Branch.objects.all().order_by('-is_active', 'name')
    return render(request, 'branches/list.html', {
        'branches': branches,
        'user_role': role,
    })

@login_required
def branch_create(request):
    role = get_user_role(request)
    if role != TenantUser.ROLE_OWNER:
        messages.error(request, "Only the workspace owner can create new branches.")
        return redirect('branch_list')

    from apps.tenants.tier_limits import can_add_branch
    if not can_add_branch(request.tenant):
        messages.error(request, "Branch limit reached for your current subscription tier.")
        return redirect('branch_list')

    if request.method == 'POST':
        form = BranchForm(request.POST)
        if form.is_valid():
            branch = form.save()
            messages.success(request, f'Branch "{branch.name}" created successfully.')
            return redirect('branch_list')
    else:
        form = BranchForm()

    return render(request, 'branches/form.html', {
        'form': form,
        'title': 'Add New Branch',
        'user_role': role,
    })

@login_required
def branch_update(request, pk):
    role = get_user_role(request)
    if role not in [TenantUser.ROLE_OWNER, TenantUser.ROLE_ADMIN]:
        return redirect('branch_list')

    branch = get_object_or_404(Branch, pk=pk)
    
    if request.method == 'POST':
        form = BranchForm(request.POST, instance=branch)
        if form.is_valid():
            form.save()
            messages.success(request, f'Branch "{branch.name}" updated successfully.')
            return redirect('branch_list')
    else:
        form = BranchForm(instance=branch)

    return render(request, 'branches/form.html', {
        'form': form,
        'title': f'Edit {branch.name}',
        'user_role': role,
        'branch': branch,
    })
