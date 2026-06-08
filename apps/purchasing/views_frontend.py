from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from apps.tenants.permissions import get_user_role
from apps.tenants.models import TenantUser
from .models import Supplier, GoodsReceivedNote, GRNItem
from apps.products.models import Product, Unit

@login_required
def supplier_list(request):
    role = get_user_role(request)
    if role not in [TenantUser.ROLE_OWNER, TenantUser.ROLE_ADMIN, TenantUser.ROLE_MANAGER, TenantUser.ROLE_AUDITOR]:
        return redirect('pos_checkout')

    suppliers = Supplier.objects.filter(is_active=True).order_by('name')
    return render(request, 'purchasing/supplier_list.html', {
        'suppliers': suppliers,
        'user_role': role,
    })

@login_required
def supplier_create(request):
    role = get_user_role(request)
    if role not in [TenantUser.ROLE_OWNER, TenantUser.ROLE_ADMIN, TenantUser.ROLE_MANAGER]:
        return redirect('supplier_list')

    if request.method == 'POST':
        name = request.POST.get('name')
        contact_person = request.POST.get('contact_person', '')
        email = request.POST.get('email', '')
        phone = request.POST.get('phone', '')
        address = request.POST.get('address', '')
        kra_pin = request.POST.get('kra_pin', '')

        if not name:
            messages.error(request, 'Supplier name is required.')
        else:
            Supplier.objects.create(
                name=name,
                contact_person=contact_person,
                email=email,
                phone=phone,
                address=address,
                kra_pin=kra_pin
            )
            messages.success(request, f'Supplier "{name}" added successfully.')
            return redirect('supplier_list')

    return render(request, 'purchasing/supplier_form.html', {
        'title': 'Add Supplier',
        'user_role': role,
    })

@login_required
def supplier_update(request, pk):
    role = get_user_role(request)
    if role not in [TenantUser.ROLE_OWNER, TenantUser.ROLE_ADMIN, TenantUser.ROLE_MANAGER]:
        return redirect('supplier_list')

    supplier = get_object_or_404(Supplier, pk=pk)

    if request.method == 'POST':
        supplier.name = request.POST.get('name')
        supplier.contact_person = request.POST.get('contact_person', '')
        supplier.email = request.POST.get('email', '')
        supplier.phone = request.POST.get('phone', '')
        supplier.address = request.POST.get('address', '')
        supplier.kra_pin = request.POST.get('kra_pin', '')
        supplier.save()
        messages.success(request, f'Supplier "{supplier.name}" updated successfully.')
        return redirect('supplier_list')

    return render(request, 'purchasing/supplier_form.html', {
        'title': f'Edit {supplier.name}',
        'supplier': supplier,
        'user_role': role,
    })

@login_required
def supplier_delete(request, pk):
    role = get_user_role(request)
    if role not in [TenantUser.ROLE_OWNER, TenantUser.ROLE_ADMIN]:
        return redirect('supplier_list')

    supplier = get_object_or_404(Supplier, pk=pk)
    supplier.is_active = False
    supplier.save()
    messages.success(request, f'Supplier "{supplier.name}" deactivated.')
    return redirect('supplier_list')


# ─────────────────────────────────────────────────────────────────────────────
# GOODS RECEIVED NOTE (GRN) FRONTEND VIEWS
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def grn_list(request):
    role = get_user_role(request)
    if role not in [TenantUser.ROLE_OWNER, TenantUser.ROLE_ADMIN, TenantUser.ROLE_MANAGER, TenantUser.ROLE_AUDITOR]:
        return redirect('pos_checkout')

    grns = GoodsReceivedNote.objects.all().select_related('supplier', 'branch', 'received_by').order_by('-created_at')
    return render(request, 'purchasing/grn_list.html', {
        'grns': grns,
        'user_role': role,
    })

@login_required
def grn_create(request):
    role = get_user_role(request)
    if role not in [TenantUser.ROLE_OWNER, TenantUser.ROLE_ADMIN, TenantUser.ROLE_MANAGER]:
        return redirect('grn_list')

    from apps.branches.models import Branch

    if request.method == 'POST':
        supplier_id = request.POST.get('supplier')
        branch_id = request.POST.get('branch') or request.session.get('branch_id')
        invoice_no = request.POST.get('supplier_invoice_number', '')
        payment_term = request.POST.get('payment_term', 'credit')
        due_date_str = request.POST.get('due_date')
        notes = request.POST.get('notes', '')

        # Items submitted via lists
        product_ids = request.POST.getlist('product_id[]')
        quantities = request.POST.getlist('quantity[]')
        unit_costs = request.POST.getlist('unit_cost[]')
        expiry_dates = request.POST.getlist('expiry_date[]')
        batch_numbers = request.POST.getlist('batch_number[]')

        if not supplier_id or not branch_id or not product_ids:
            messages.error(request, 'Please complete all required fields and add at least one product.')
        else:
            supplier = get_object_or_404(Supplier, pk=supplier_id)
            branch = get_object_or_404(Branch, pk=branch_id)
            
            due_date = None
            if payment_term == 'credit' and due_date_str:
                from datetime import date
                try:
                    due_date = date.fromisoformat(due_date_str)
                except ValueError:
                    pass

            # Auto generate unique GRN Number
            grn_number = f"GRN-{timezone.now().strftime('%Y%m%d%H%M%S')}"

            with transaction.atomic():
                grn = GoodsReceivedNote.objects.create(
                    grn_number=grn_number,
                    supplier=supplier,
                    branch=branch,
                    received_by=request.user,
                    supplier_invoice_number=invoice_no,
                    payment_term=payment_term,
                    due_date=due_date,
                    notes=notes
                )

                for i in range(len(product_ids)):
                    prod = get_object_or_404(Product, pk=product_ids[i])
                    qty = float(quantities[i])
                    cost = float(unit_costs[i])
                    exp = expiry_dates[i] if (i < len(expiry_dates) and expiry_dates[i]) else None
                    bat = batch_numbers[i] if (i < len(batch_numbers) and batch_numbers[i]) else f"BAT-{grn_number}"

                    GRNItem.objects.create(
                        grn=grn,
                        product=prod,
                        quantity_purchase_units=qty,
                        purchase_unit=prod.purchase_unit or prod.sale_unit,
                        unit_cost=cost,
                        expiry_date=exp,
                        batch_number=bat
                    )

                # Process stock updates and payables balance in backend service
                from .services import GRNService
                warnings = GRNService.receive(grn)

                for w in warnings:
                    messages.warning(request, w)

            messages.success(request, f'Goods Received Note {grn.grn_number} successfully recorded!')
            return redirect('grn_list')

    suppliers = Supplier.objects.filter(is_active=True).order_by('name')
    branches = Branch.objects.filter(is_active=True).order_by('name')
    products = Product.objects.filter(is_active=True).order_by('name')

    return render(request, 'purchasing/grn_form.html', {
        'suppliers': suppliers,
        'branches': branches,
        'products': products,
        'user_role': role,
    })
