from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum, F, Count, Q
from django.http import JsonResponse
from django.contrib import messages
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
    profit_today = SaleItem.objects.filter(
        sale__created_at__date=today,
        sale__status='completed'
    ).aggregate(
        total_profit=Sum(F('line_total') - (F('quantity') * F('cost_price')))
    )['total_profit'] or 0

    # 3. Low Stock Items
    low_stock_query = BranchStock.objects.filter(
        quantity__lte=F('product__minimum_stock_level')
    )
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
    try:
        for sale in failed_sales:
            sign_sale_etims.delay(sale.id, request.tenant.schema_name)
        return JsonResponse({'status': 'success', 'count': count})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f"Failed to queue background tasks (Redis/Celery offline): {str(e)}"}, status=500)

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

    month = int(request.GET.get('month', timezone.now().month))
    year  = int(request.GET.get('year',  timezone.now().year))

    # Revenue
    revenue = Sale.objects.filter(
        created_at__year=year, created_at__month=month, status='completed'
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    # COGS
    cogs = SaleItem.objects.filter(
        sale__created_at__year=year, sale__created_at__month=month, sale__status='completed'
    ).aggregate(total=Sum(F('quantity') * F('cost_price')))['total'] or 0

    gross_profit = revenue - cogs

    # OPEX
    total_expenses = Expense.objects.filter(
        paid_on__year=year, paid_on__month=month
    ).aggregate(total=Sum('amount'))['total'] or 0

    net_profit = gross_profit - total_expenses

    gross_margin   = (gross_profit / revenue * 100) if revenue > 0 else 0
    expense_ratio  = (total_expenses / revenue * 100) if revenue > 0 else 0

    expense_breakdown = Expense.objects.filter(
        paid_on__year=year, paid_on__month=month
    ).values('category__name').annotate(total=Sum('amount')).order_by('-total')

    months = range(1, 13)
    years  = range(2024, timezone.now().year + 1)

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


# ─────────────────────────────────────────────────────────────────────────────
# CREDIT AGING — TRADE RECEIVABLES
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def credit_aging_report(request):
    """Receivables aging table — all customers with outstanding credit."""
    role = get_user_role(request)
    if role not in ['owner', 'admin', 'manager', 'auditor']:
        return redirect('dashboard')

    from apps.reports.services import ReportService
    aging_rows = ReportService.credit_aging()

    totals = {
        'balance':  sum(r['balance']  for r in aging_rows),
        'current':  sum(r['current']  for r in aging_rows),
        'd31_60':   sum(r['d31_60']   for r in aging_rows),
        'd61_90':   sum(r['d61_90']   for r in aging_rows),
        'over_90':  sum(r['over_90']  for r in aging_rows),
    }

    return render(request, 'reports/credit_aging.html', {
        'user_role': role,
        'aging_rows': aging_rows,
        'totals': totals,
    })


@login_required
def record_credit_payment(request, customer_id):
    """POST: record a repayment from a credit customer."""
    role = get_user_role(request)
    if role not in ['owner', 'admin', 'manager']:
        return redirect('dashboard')

    from apps.customers.models import Customer, CustomerCreditLedger

    customer = get_object_or_404(Customer, pk=customer_id)

    if request.method == 'POST':
        amount    = request.POST.get('amount')
        reference = request.POST.get('reference', '')
        notes     = request.POST.get('notes', '')
        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError
        except (TypeError, ValueError):
            messages.error(request, 'Enter a valid positive amount.')
            return redirect('credit_aging_report')

        CustomerCreditLedger.objects.create(
            customer=customer,
            transaction_type='payment',
            amount=amount,
            reference=reference,
            notes=notes,
            recorded_by=request.user,
        )
        # Reduce outstanding balance
        from decimal import Decimal
        customer.current_credit_balance = max(
            Decimal('0.00'), customer.current_credit_balance - Decimal(str(amount))
        )
        customer.save(update_fields=['current_credit_balance'])
        messages.success(request, f'Payment of KES {amount:,.2f} recorded for {customer.name}.')

    return redirect('credit_aging_report')


# ─────────────────────────────────────────────────────────────────────────────
# TRADE PAYABLES — SUPPLIER LEDGER
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def payables_report(request):
    """Supplier payables summary — amounts owed to vendors."""
    role = get_user_role(request)
    if role not in ['owner', 'admin']:
        return redirect('dashboard')

    from apps.reports.services import ReportService
    from apps.purchasing.models import Supplier

    payables = ReportService.payables_summary()
    total_owed = sum(r['balance'] for r in payables)

    # Also list suppliers with zero balance for payment form
    all_suppliers = Supplier.objects.filter(is_active=True).order_by('name')

    return render(request, 'reports/payables.html', {
        'user_role': role,
        'payables': payables,
        'total_owed': total_owed,
        'all_suppliers': all_suppliers,
    })


@login_required
def record_supplier_payment(request, supplier_id):
    """POST: record a payment to a supplier."""
    role = get_user_role(request)
    if role not in ['owner', 'admin']:
        return redirect('dashboard')

    from apps.purchasing.models import Supplier, SupplierPayment

    supplier = get_object_or_404(Supplier, pk=supplier_id)

    if request.method == 'POST':
        amount    = request.POST.get('amount')
        method    = request.POST.get('payment_method', 'bank_transfer')
        reference = request.POST.get('transaction_reference', '')
        notes     = request.POST.get('notes', '')
        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError
        except (TypeError, ValueError):
            messages.error(request, 'Enter a valid positive amount.')
            return redirect('payables_report')

        SupplierPayment.objects.create(
            supplier=supplier,
            amount=amount,
            payment_method=method,
            transaction_reference=reference,
            notes=notes,
            paid_by=request.user,
        )
        from decimal import Decimal
        supplier.current_payable_balance = max(
            Decimal('0.00'), supplier.current_payable_balance - Decimal(str(amount))
        )
        supplier.save(update_fields=['current_payable_balance'])
        messages.success(request, f'Payment of KES {amount:,.2f} to {supplier.name} recorded.')

    return redirect('payables_report')


# ─────────────────────────────────────────────────────────────────────────────
# STAFF PERFORMANCE
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def staff_performance_report(request):
    """Cashier-level sales productivity for a date range."""
    role = get_user_role(request)
    if role not in ['owner', 'admin']:
        return redirect('dashboard')

    from apps.reports.services import ReportService
    from apps.branches.models import Branch

    branch_id  = request.GET.get('branch') or request.session.get('branch_id')
    start_str  = request.GET.get('start')
    end_str    = request.GET.get('end')

    today      = timezone.now().date()
    start_date = today.replace(day=1)
    end_date   = today

    if start_str:
        try:
            from datetime import date
            start_date = date.fromisoformat(start_str)
        except ValueError:
            pass
    if end_str:
        try:
            from datetime import date
            end_date = date.fromisoformat(end_str)
        except ValueError:
            pass

    branch = None
    if branch_id:
        branch = Branch.objects.filter(pk=branch_id).first()

    perf_rows = []
    if branch:
        perf_rows = ReportService.cashier_performance(branch, start_date, end_date)

    branches = Branch.objects.filter(is_active=True).order_by('name')

    return render(request, 'reports/staff_performance.html', {
        'user_role':   role,
        'perf_rows':   perf_rows,
        'branches':    branches,
        'branch':      branch,
        'start_date':  start_date,
        'end_date':    end_date,
    })





