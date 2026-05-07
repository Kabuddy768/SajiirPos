from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.tenants.permissions import get_user_role
from apps.branches.models import Branch
from .models import Expense, ExpenseCategory
from .forms import ExpenseForm

@login_required
def expense_list(request):
    role = get_user_role(request)
    if role not in ['owner', 'admin', 'manager']:
        return redirect('dashboard')

    expenses = Expense.objects.select_related('branch', 'category', 'recorded_by').order_by('-paid_on')
    
    branch_id = request.GET.get('branch')
    if branch_id:
        expenses = expenses.filter(branch_id=branch_id)

    branches = Branch.objects.filter(is_active=True)
    return render(request, 'expenses/list.html', {
        'expenses': expenses,
        'branches': branches,
        'user_role': role,
    })

@login_required
def expense_create(request):
    role = get_user_role(request)
    if role not in ['owner', 'admin', 'manager']:
        return redirect('expense_list')

    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.recorded_by = request.user
            expense.save()
            messages.success(request, "Expense recorded successfully.")
            return redirect('expense_list')
    else:
        form = ExpenseForm()

    return render(request, 'expenses/form.html', {
        'form': form,
        'title': 'Record New Expense',
        'user_role': role,
    })

@login_required
def expense_delete(request, pk):
    role = get_user_role(request)
    if role not in ['owner', 'admin']:
        return redirect('expense_list')

    expense = get_object_or_404(Expense, pk=pk)
    expense.delete()
    messages.warning(request, "Expense record deleted.")
    return redirect('expense_list')
