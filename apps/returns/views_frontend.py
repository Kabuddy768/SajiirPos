from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.tenants.permissions import get_user_role
from apps.sales.models import Sale, SaleItem
from .services import ReturnService, ReturnApprovalRequired, InvalidReturnError, RETURN_APPROVAL_THRESHOLD

@login_required
def process_return(request, sale_id):
    """
    UI for selecting items to return from a specific sale.
    """
    role = get_user_role(request)
    if role not in ['owner', 'admin', 'manager']:
        messages.error(request, "Only managers can process returns.")
        return redirect('sale_list')

    sale = get_object_or_404(Sale.objects.prefetch_related('items__product'), pk=sale_id)
    
    if request.method == 'POST':
        # items_data format: [{'sale_item_id': 1, 'quantity': 2}]
        items_data = []
        for item in sale.items.all():
            qty = request.POST.get(f'qty_{item.id}', 0)
            if qty and float(qty) > 0:
                items_data.append({
                    'sale_item_id': item.id,
                    'quantity': float(qty)
                })

        if not items_data:
            messages.error(request, "Please select at least one item to return.")
        else:
            reason = request.POST.get('reason', 'Damaged/Returned')
            refund_method = request.POST.get('refund_method', 'cash')
            notes = request.POST.get('notes', '')
            
            try:
                ReturnService.process(
                    original_sale=sale,
                    items_data=items_data,
                    reason=reason,
                    refund_method=refund_method,
                    cashier=request.user,
                    # For now, if role is manager+, we pass user as approved_by if threshold hit
                    approved_by=request.user if role in ['owner', 'admin', 'manager'] else None,
                    notes=notes
                )
                messages.success(request, f"Return processed successfully for Sale {sale.sale_number}.")
                return redirect('sale_detail', pk=sale.id)
            except (ReturnApprovalRequired, InvalidReturnError) as e:
                messages.error(request, str(e))

    return render(request, 'returns/process.html', {
        'sale': sale,
        'user_role': role,
        'threshold': RETURN_APPROVAL_THRESHOLD,
    })
