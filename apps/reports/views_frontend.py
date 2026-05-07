from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum, F, Count, Q
from django.http import JsonResponse
from apps.tenants.permissions import get_user_role

from apps.tenants.models import TenantUser


@login_required
def dashboard(request):
    if request.tenant.schema_name == 'public':
        return redirect('/admin/')

    role = get_user_role(request)
    if role not in [TenantUser.ROLE_OWNER, TenantUser.ROLE_ADMIN, TenantUser.ROLE_MANAGER, TenantUser.ROLE_AUDITOR]:
        return redirect('pos_checkout')

    # KPI Metrics
    today = timezone.now().date()
    from apps.sales.models import Sale, SaleItem
    from apps.inventory.models import BranchStock
    
    # 1. Total Sales Today
    sales_today = Sale.objects.filter(
        created_at__date=today,
        status='completed'
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # 2. Total Profit Today
    # Profit = (Unit Price - Cost Price) * Quantity
    profit_today = SaleItem.objects.filter(
        sale__created_at__date=today,
        sale__status='completed'
    ).aggregate(
        total_profit=Sum(F('line_total') - (F('quantity') * F('cost_price')))
    )['total_profit'] or 0
    
    # 3. Low Stock Items (Across all branches if Owner/Admin, or current branch if Manager)
    low_stock_query = BranchStock.objects.filter(
        quantity__lte=F('product__minimum_stock_level')
    )
    # If we have a branch in session, filter by it
    branch_id = request.session.get('branch_id')
    if branch_id:
        low_stock_query = low_stock_query.filter(branch_id=branch_id)
        
    low_stock_count = low_stock_query.count()
    
    # 4. Recent Sales
    recent_sales = Sale.objects.filter(
        status='completed'
    ).select_related('cashier', 'customer').order_by('-created_at')[:10]

    return render(request, 'reports/dashboard.html', {
        'user_role': role,
        'sales_today': sales_today,
        'profit_today': profit_today,
        'low_stock_count': low_stock_count,
        'recent_sales': recent_sales,
    })


@login_required
def etims_dashboard(request):
    role = get_user_role(request)
    if role not in [TenantUser.ROLE_OWNER, TenantUser.ROLE_ADMIN]:
        return redirect('dashboard')
    
    from apps.sales.models import Sale
    stats = Sale.objects.aggregate(
        total=Count('id'),
        pending=Count('id', filter=Q(etims_submission_status='pending')),
        submitted=Count('id', filter=Q(etims_submission_status='submitted')),
        failed=Count('id', filter=Q(etims_submission_status='failed'))
    )
    
    return render(request, 'reports/etims_dashboard.html', {
        'user_role': role,
        'stats': stats
    })

@login_required
def etims_retry_all(request):
    from apps.sales.models import Sale
    from workers.etims_tasks import sign_sale_etims
    
    failed_sales = Sale.objects.filter(etims_submission_status='failed')
    count = failed_sales.count()
    for sale in failed_sales:
        sign_sale_etims.delay(sale.id, request.tenant.schema_name)
        
    return JsonResponse({'status': 'success', 'count': count})

@login_required
def etims_pending_invoices(request):
    from apps.sales.models import Sale
    pending_sales = Sale.objects.filter(etims_submission_status='pending').order_by('-created_at')
    return render(request, 'reports/etims_pending.html', {'sales': pending_sales})



@login_required
def dashboard_staff(request):
    """Staff management page — Owner/Admin only."""
    role = get_user_role(request)
    if role not in [TenantUser.ROLE_OWNER, TenantUser.ROLE_ADMIN]:
        return redirect('dashboard')

    from apps.invitations.models import StaffInvitation

    staff_members = TenantUser.objects.filter(
        tenant=request.tenant,
    ).select_related('user').order_by('-join_date')

    pending_invitations = StaffInvitation.objects.filter(
        is_used=False,
        expires_at__gt=timezone.now(),
    ).select_related('invited_by', 'branch').order_by('-created_at')

    return render(request, 'dashboard/staff.html', {
        'user_role': role,
        'staff_members': staff_members,
        'pending_invitations': pending_invitations,
    })

@login_required
def profit_loss_report(request):
    role = get_user_role(request)
    if role not in ['owner', 'admin', 'manager']:
        return redirect('dashboard')

    from apps.sales.models import Sale, SaleItem
    from apps.expenses.models import Expense
    from django.db.models import Sum, F
    
    # Filter by month/year
    month = int(request.GET.get('month', timezone.now().month))
    year = int(request.GET.get('year', timezone.now().year))
    
    # 1. Total Revenue
    revenue = Sale.objects.filter(
        created_at__year=year,
        created_at__month=month,
        status='completed'
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # 2. Cost of Goods Sold (COGS)
    cogs = SaleItem.objects.filter(
        sale__created_at__year=year,
        sale__created_at__month=month,
        sale__status='completed'
    ).aggregate(total=Sum(F('quantity') * F('cost_price')))['total'] or 0
    
    gross_profit = revenue - cogs
    
    # 3. Operating Expenses
    total_expenses = Expense.objects.filter(
        paid_on__year=year,
        paid_on__month=month
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    net_profit = gross_profit - total_expenses
    
    # Ratios
    gross_margin = (gross_profit / revenue * 100) if revenue > 0 else 0
    expense_ratio = (total_expenses / revenue * 100) if revenue > 0 else 0

    # Expense Breakdown
    expense_breakdown = Expense.objects.filter(
        paid_on__year=year,
        paid_on__month=month
    ).values('category__name').annotate(total=Sum('amount')).order_by('-total')

    months = range(1, 13)
    years = range(2024, timezone.now().year + 1)

    return render(request, 'reports/profit_loss.html', {
        'user_role': role,
        'revenue': revenue,
        'cogs': cogs,
        'gross_profit': gross_profit,
        'total_expenses': total_expenses,
        'net_profit': net_profit,
        'gross_margin': gross_margin,
        'expense_ratio': expense_ratio,
        'expense_breakdown': expense_breakdown,
        'selected_month': month,
        'selected_year': year,
        'months': months,
        'years': years,
    })



