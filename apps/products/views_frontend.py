from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from apps.tenants.permissions import get_user_role
from apps.tenants.models import TenantUser
from .models import Product, Category
from .forms import ProductForm

@login_required
def product_list(request):
    role = get_user_role(request)
    if role not in [TenantUser.ROLE_OWNER, TenantUser.ROLE_ADMIN, TenantUser.ROLE_MANAGER, TenantUser.ROLE_AUDITOR]:
        return redirect('pos_checkout')

    search_query = request.GET.get('q', '')
    category_id = request.GET.get('category', '')

    products = Product.objects.all().select_related('category', 'sale_unit')

    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(sku__icontains=search_query) |
            Q(barcode__icontains=search_query)
        )

    if category_id:
        products = products.filter(category_id=category_id)

    categories = Category.objects.all()

    return render(request, 'products/list.html', {
        'products': products,
        'categories': categories,
        'user_role': role,
        'search_query': search_query,
        'selected_category': category_id,
    })

@login_required
def product_create(request):
    role = get_user_role(request)
    if role not in [TenantUser.ROLE_OWNER, TenantUser.ROLE_ADMIN, TenantUser.ROLE_MANAGER]:
        return redirect('product_list')

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.created_by = request.user
            product.save()
            messages.success(request, f'Product "{product.name}" created successfully.')
            return redirect('product_list')
    else:
        form = ProductForm()

    return render(request, 'products/form.html', {
        'form': form,
        'title': 'Add New Product',
        'user_role': role,
    })

@login_required
def product_update(request, pk):
    role = get_user_role(request)
    if role not in [TenantUser.ROLE_OWNER, TenantUser.ROLE_ADMIN, TenantUser.ROLE_MANAGER]:
        return redirect('product_list')

    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f'Product "{product.name}" updated successfully.')
            return redirect('product_list')
    else:
        form = ProductForm(instance=product)

    return render(request, 'products/form.html', {
        'form': form,
        'title': f'Edit {product.name}',
        'user_role': role,
        'product': product,
    })

@login_required
def product_delete(request, pk):
    role = get_user_role(request)
    if role not in [TenantUser.ROLE_OWNER, TenantUser.ROLE_ADMIN]:
        return redirect('product_list')

    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        product.is_active = False
        product.save()
        messages.success(request, f'Product "{product.name}" deactivated.')
        return redirect('product_list')

    return render(request, 'products/confirm_delete.html', {
        'product': product,
        'user_role': role,
    })
