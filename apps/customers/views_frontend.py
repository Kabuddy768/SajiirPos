from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.tenants.permissions import get_user_role
from .models import Customer, LoyaltyTier
from .forms import CustomerForm

@login_required
def customer_list(request):
    role = get_user_role(request)
    if role not in ['owner', 'admin', 'manager', 'cashier']:
        return redirect('dashboard')

    q = request.GET.get('q', '')
    customers = Customer.objects.filter(is_active=True).order_by('-created_at')
    
    if q:
        customers = customers.filter(name__icontains=q) | customers.filter(phone__icontains=q)

    return render(request, 'customers/list.html', {
        'customers': customers,
        'search_query': q,
        'user_role': role,
    })

@login_required
def customer_create(request):
    role = get_user_role(request)
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save()
            messages.success(request, f"Customer {customer.name} added.")
            return redirect('customer_list')
    else:
        form = CustomerForm()

    return render(request, 'customers/form.html', {
        'form': form,
        'title': 'Add New Customer',
        'user_role': role,
    })

@login_required
def customer_update(request, pk):
    role = get_user_role(request)
    customer = get_object_or_404(Customer, pk=pk)
    
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, f"Customer {customer.name} updated.")
            return redirect('customer_list')
    else:
        form = CustomerForm(instance=customer)

    return render(request, 'customers/form.html', {
        'form': form,
        'title': f'Edit {customer.name}',
        'user_role': role,
        'customer': customer,
    })

@login_required
def customer_detail(request, pk):
    role = get_user_role(request)
    customer = get_object_or_404(Customer, pk=pk)
    from apps.sales.models import Sale
    sales = Sale.objects.filter(customer_phone=customer.phone).order_by('-created_at')[:10]
    
    return render(request, 'customers/detail.html', {
        'customer': customer,
        'sales': sales,
        'user_role': role,
    })
