from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from .models import CashSession, Sale
from apps.products.models import Product
from apps.branches.models import Branch
from apps.tenants.permissions import get_user_role


@login_required
def session_open(request):
    if request.tenant.schema_name == 'public':
        return redirect('/admin/')
    
    # Check if there is already an open session
    open_session = CashSession.objects.filter(cashier=request.user, status='open').first()
    if open_session:
        return redirect('pos_checkout')

    if request.method == 'POST':
        opening_float = request.POST.get('opening_float', 0)
        from apps.branches.models import StaffProfile
        try:
            profile = StaffProfile.objects.get(user=request.user, is_active=True)
            branch = profile.branch
        except StaffProfile.DoesNotExist:
            return render(request, 'pos/session_open.html', {'error': 'User not assigned to a branch'})
            
        session = CashSession.objects.create(
            branch=branch,
            cashier=request.user,
            opening_float=opening_float,
            status='open'
        )
        return redirect('pos_checkout')
    
    return render(request, 'pos/session_open.html')

@login_required
def checkout(request):
    if request.tenant.schema_name == 'public':
        return redirect('/admin/')
    
    session = CashSession.objects.filter(cashier=request.user, status='open').first()
    if not session:
        return redirect('session_open')
    
    return render(request, 'pos/checkout.html', {'session': session})

@login_required
def session_close(request):
    if request.tenant.schema_name == 'public':
        return redirect('/admin/')
    
    session = CashSession.objects.filter(cashier=request.user, status='open').first()
    if not session:
        return redirect('session_open')
    
    if request.method == 'POST':
        closing_float = request.POST.get('closing_float', 0)
        session.closing_float = closing_float
        session.status = 'closed'
        session.closed_at = timezone.now()
        session.save()
        return redirect('z_report', session_id=session.id)
    
    # Simple Z-report preview
    sales = session.sales.all()
    total_sales = sum(s.total_amount for s in sales)
    
    return render(request, 'pos/session_close.html', {
        'session': session,
        'total_sales': total_sales,
        'sales_count': sales.count()
    })

@login_required
def z_report(request, session_id):
    if request.tenant.schema_name == 'public':
        return redirect('/admin/')
    
    session = get_object_or_404(CashSession, id=session_id)
    sales = session.sales.all()
    total_sales = sum(s.total_amount for s in sales)
    return render(request, 'pos/z_report.html', {
        'session': session,
        'sales': sales,
        'total_sales': total_sales
    })

@login_required
def product_lookup(request):
    barcode = request.GET.get('barcode', '').strip()
    if not barcode:
        return JsonResponse({'found': False, 'error': 'No barcode'})
    try:
        # Check active products first
        product = Product.objects.get(barcode=barcode, is_active=True)
        return JsonResponse({'found': True, 'product': {
            'id': product.id,
            'name': product.name,
            'selling_price': float(product.selling_price),
            'cost_price': float(product.cost_price),
            'sku': product.sku,
            'barcode': product.barcode,
            'tax_type': product.tax_type,
            'is_tax_inclusive': product.is_tax_inclusive,
            'is_weighable': product.is_weighable,
            'unit': product.sale_unit.short_name if product.sale_unit else 'PCS',
        }})
    except Product.DoesNotExist:
        return JsonResponse({'found': False, 'error': 'Not found'})

# ── Week 5: Advanced Sales & Reporting ──────────────────────────

@login_required
def sale_list(request):
    role = get_user_role(request)
    if role not in ['owner', 'admin', 'manager', 'auditor']:
        return redirect('pos_checkout')

    from django.db.models import Q
    
    branch_id = request.GET.get('branch')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    q = request.GET.get('q', '')

    sales = Sale.objects.select_related('branch', 'cashier', 'session').order_by('-created_at')

    if branch_id:
        sales = sales.filter(branch_id=branch_id)
    if date_from:
        sales = sales.filter(created_at__date__gte=date_from)
    if date_to:
        sales = sales.filter(created_at__date__lte=date_to)
    if q:
        sales = sales.filter(
            Q(sale_number__icontains=q) |
            Q(customer_name__icontains=q) |
            Q(customer_phone__icontains=q)
        )

    from django.core.paginator import Paginator
    paginator = Paginator(sales, 20)  # 20 per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    branches = Branch.objects.filter(is_active=True)
    
    return render(request, 'sales/sale_list.html', {
        'sales': page_obj,
        'branches': branches,
        'user_role': role,
    })


@login_required
def sale_detail(request, pk):
    role = get_user_role(request)
    sale = get_object_or_404(Sale.objects.prefetch_related('items__product'), pk=pk)
    
    return render(request, 'sales/sale_detail.html', {
        'sale': sale,
        'user_role': role,
    })

