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

import csv
import io
from decimal import Decimal, InvalidOperation
from django.db import transaction
from django.utils.crypto import get_random_string

@login_required
def product_import(request):
    role = get_user_role(request)
    if role not in [TenantUser.ROLE_OWNER, TenantUser.ROLE_ADMIN, TenantUser.ROLE_MANAGER]:
        messages.error(request, "You do not have permission to import products.")
        return redirect('product_list')

    if request.method == 'POST':
        csv_file = request.FILES.get('file')
        if not csv_file or not csv_file.name.endswith('.csv'):
            messages.error(request, "Please upload a valid CSV file.")
            return redirect('product_import')

        # Read CSV data
        try:
            data_set = csv_file.read().decode('utf-8')
            io_string = io.StringIO(data_set)
            reader = csv.DictReader(io_string)
        except Exception as e:
            messages.error(request, f"Error reading file: {e}")
            return redirect('product_import')

        success_count = 0
        skipped_rows = []
        
        # Get or create default fallback category and unit
        default_category, _ = Category.objects.get_or_create(name="General")
        default_unit, _ = Unit.objects.get_or_create(short_name="pcs", defaults={'name': 'Pieces'})

        with transaction.atomic():
            for idx, row in enumerate(reader, start=1):
                name = (row.get('name') or '').strip()
                if not name:
                    skipped_rows.append(f"Row {idx}: Missing product name")
                    continue

                sku = (row.get('sku') or '').strip()
                if not sku:
                    # Auto-generate a unique SKU
                    sku = f"SKU-{get_random_string(8).upper()}"
                
                # Check SKU uniqueness
                if Product.objects.filter(sku=sku).exists():
                    skipped_rows.append(f"Row {idx}: SKU '{sku}' already exists.")
                    continue

                barcode = (row.get('barcode') or '').strip() or None
                if barcode and Product.objects.filter(barcode=barcode).exists():
                    skipped_rows.append(f"Row {idx}: Barcode '{barcode}' already exists.")
                    continue

                # Category fallback
                cat_name = (row.get('category') or '').strip()
                if cat_name:
                    category, _ = Category.objects.get_or_create(name=cat_name)
                else:
                    category = default_category

                # Unit fallback
                unit_name = (row.get('unit') or '').strip()
                if unit_name:
                    sale_unit, _ = Unit.objects.get_or_create(short_name=unit_name, defaults={'name': unit_name})
                else:
                    sale_unit = default_unit

                # Prices
                try:
                    cost_price = Decimal(str(row.get('cost_price') or '0.00').strip() or '0.00')
                    selling_price = Decimal(str(row.get('selling_price') or '0.00').strip() or '0.00')
                except (InvalidOperation, ValueError):
                    skipped_rows.append(f"Row {idx}: Invalid prices.")
                    continue

                if selling_price < cost_price:
                    # Adjust selling price to avoid validation error
                    selling_price = cost_price

                desc = (row.get('description') or '').strip()

                try:
                    Product.objects.create(
                        name=name,
                        sku=sku,
                        barcode=barcode,
                        category=category,
                        sale_unit=sale_unit,
                        cost_price=cost_price,
                        selling_price=selling_price,
                        description=desc,
                        created_by=request.user
                    )
                    success_count += 1
                except Exception as e:
                    skipped_rows.append(f"Row {idx}: Database error: {e}")

        if success_count > 0:
            messages.success(request, f"Successfully imported {success_count} products.")
        if skipped_rows:
            messages.warning(request, f"Skipped {len(skipped_rows)} rows due to validation or duplication errors.")

        return render(request, 'products/import_result.html', {
            'success_count': success_count,
            'skipped_rows': skipped_rows,
            'user_role': role
        })

    return render(request, 'products/import.html', {
        'user_role': role
    })

@login_required
def product_barcode(request, pk):
    role = get_user_role(request)
    if role not in [TenantUser.ROLE_OWNER, TenantUser.ROLE_ADMIN, TenantUser.ROLE_MANAGER]:
        return redirect('product_list')

    product = get_object_or_404(Product, pk=pk)
    tenant = request.tenant
    
    return render(request, 'products/barcode.html', {
        'product': product,
        'tenant': tenant,
        'user_role': role,
    })
