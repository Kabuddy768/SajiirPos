from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import F, Q
from apps.tenants.permissions import get_user_role
from apps.tenants.models import TenantUser
from apps.branches.models import Branch
from apps.products.models import Product
from .models import BranchStock, StockMovement, StockTransfer, StockTransferItem
from .transfer_service import TransferService, TransferError

@login_required
def stock_list(request):
    role = get_user_role(request)
    if role not in [TenantUser.ROLE_OWNER, TenantUser.ROLE_ADMIN, TenantUser.ROLE_MANAGER, TenantUser.ROLE_AUDITOR]:
        return redirect('pos_checkout')

    branch_id = request.GET.get('branch', request.session.get('branch_id'))
    q = request.GET.get('q', '')
    only_low_stock = request.GET.get('low_stock') == '1'

    stocks = BranchStock.objects.select_related('product', 'branch', 'product__category', 'product__primary_supplier')

    if branch_id:
        stocks = stocks.filter(branch_id=branch_id)
    
    if q:
        stocks = stocks.filter(
            Q(product__name__icontains=q) |
            Q(product__sku__icontains=q) |
            Q(product__barcode__icontains=q)
        )

    if only_low_stock:
        stocks = stocks.filter(quantity__lte=F('product__minimum_stock_level'))

    branches = Branch.objects.filter(is_active=True)

    return render(request, 'inventory/stock_list.html', {
        'stocks': stocks,
        'branches': branches,
        'selected_branch': int(branch_id) if branch_id else None,
        'search_query': q,
        'only_low_stock': only_low_stock,
        'user_role': role,
    })

@login_required
def stock_movements(request):
    role = get_user_role(request)
    if role not in [TenantUser.ROLE_OWNER, TenantUser.ROLE_ADMIN, TenantUser.ROLE_MANAGER, TenantUser.ROLE_AUDITOR]:
        return redirect('pos_checkout')

    movements_list = StockMovement.objects.select_related('product', 'branch', 'performed_by').order_by('-created_at')
    
    from django.core.paginator import Paginator
    paginator = Paginator(movements_list, 50)  # 50 per page for logs
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'inventory/movements.html', {
        'movements': page_obj,
        'user_role': role,
    })


@login_required
def transfer_list(request):
    role = get_user_role(request)
    if role not in [TenantUser.ROLE_OWNER, TenantUser.ROLE_ADMIN, TenantUser.ROLE_MANAGER]:
        return redirect('pos_checkout')

    transfers = StockTransfer.objects.select_related('from_branch', 'to_branch', 'requested_by').order_by('-created_at')

    return render(request, 'inventory/transfer_list.html', {
        'transfers': transfers,
        'user_role': role,
    })

@login_required
def transfer_detail(request, pk):
    role = get_user_role(request)
    transfer = get_object_or_404(StockTransfer, pk=pk)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        try:
            if action == 'approve':
                TransferService.approve(transfer, request.user)
                messages.success(request, "Transfer approved.")
            elif action == 'ship':
                TransferService.ship(transfer, request.user)
                messages.success(request, "Transfer shipped. Stock deducted from source.")
            elif action == 'receive':
                TransferService.receive(transfer, request.user)
                messages.success(request, "Transfer received. Stock added to destination.")
            elif action == 'cancel':
                TransferService.cancel(transfer, request.user)
                messages.warning(request, "Transfer cancelled.")
            
            return redirect('transfer_detail', pk=transfer.pk)
        except TransferError as e:
            messages.error(request, str(e))

    return render(request, 'inventory/transfer_detail.html', {
        'transfer': transfer,
        'user_role': role,
    })
