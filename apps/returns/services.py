import uuid
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum

from apps.inventory.services import StockService
from apps.audit.utils import log_action
from .models import Return, ReturnItem


# Project Guide: returns above KES 5,000 require manager approval
RETURN_APPROVAL_THRESHOLD = Decimal('5000.00')


class ReturnApprovalRequired(Exception):
    """Raised when a return exceeds the threshold and no manager has approved it."""
    pass


class InvalidReturnError(Exception):
    """Raised for validation failures (wrong sale, over-return, etc.)."""
    pass


class ReturnService:
    @staticmethod
    def process(original_sale, items_data, reason, refund_method, cashier, approved_by=None, notes=''):
        """
        Process a return against an original sale.

        items_data: list of dicts with keys:
            - sale_item_id: int  (PK of the SaleItem being returned)
            - quantity: Decimal   (how many units to return)

        Business rules enforced:
        1. The original sale must be in 'completed' status.
        2. Return quantity must not exceed the originally-sold quantity
           minus any previously-returned quantity for that SaleItem.
        3. If total refund >= KES 5,000 the approved_by field is required.
        4. Stock is restored to the branch via StockService.adjust(reason='return').
        5. The original sale status is flipped to 'refunded' or 'partial_refund'.
        """
        from apps.sales.models import SaleItem  # avoid circular import

        if original_sale.status not in ('completed', 'partial_refund'):
            raise InvalidReturnError(
                f"Cannot return against sale {original_sale.sale_number} — "
                f"status is '{original_sale.status}'."
            )

        branch = original_sale.branch

        with transaction.atomic():
            # ----------------------------------------------------------
            # 1. Validate each item and compute refund total
            # ----------------------------------------------------------
            processed_items = []
            refund_total = Decimal('0.00')

            for item_data in items_data:
                try:
                    sale_item = SaleItem.objects.get(
                        id=item_data['sale_item_id'],
                        sale=original_sale
                    )
                except SaleItem.DoesNotExist:
                    raise InvalidReturnError(
                        f"SaleItem {item_data['sale_item_id']} does not belong to "
                        f"sale {original_sale.sale_number}."
                    )

                qty_to_return = Decimal(str(item_data['quantity']))
                if qty_to_return <= 0:
                    raise InvalidReturnError("Return quantity must be positive.")

                # How much has already been returned for this SaleItem?
                already_returned = (
                    ReturnItem.objects
                    .filter(sale_item=sale_item)
                    .aggregate(total=Sum('quantity'))['total']
                ) or Decimal('0.000')

                returnable = sale_item.quantity - already_returned
                if qty_to_return > returnable:
                    raise InvalidReturnError(
                        f"Cannot return {qty_to_return} of {sale_item.product.name}. "
                        f"Only {returnable} remaining (sold {sale_item.quantity}, "
                        f"already returned {already_returned})."
                    )

                # Line refund = (unit_price * qty) proportional to original
                line_refund = sale_item.unit_price * qty_to_return
                refund_total += line_refund

                processed_items.append({
                    'sale_item': sale_item,
                    'quantity': qty_to_return,
                    'unit_price': sale_item.unit_price,
                    'line_total': line_refund,
                })

            # ----------------------------------------------------------
            # 2. Approval check  (KES 5,000 threshold)
            # ----------------------------------------------------------
            if refund_total >= RETURN_APPROVAL_THRESHOLD and approved_by is None:
                raise ReturnApprovalRequired(
                    f"Refund of KES {refund_total} requires manager approval "
                    f"(threshold is KES {RETURN_APPROVAL_THRESHOLD})."
                )

            # ----------------------------------------------------------
            # 3. Generate return number
            # ----------------------------------------------------------
            date_str = original_sale.created_at.strftime('%Y%m%d')
            suffix = uuid.uuid4().hex[:6].upper()
            return_number = f"RTN-{branch.etims_branch_code or 'BR'}-{date_str}-{suffix}"

            # ----------------------------------------------------------
            # 4. Create Return header
            # ----------------------------------------------------------
            return_obj = Return.objects.create(
                return_number=return_number,
                original_sale=original_sale,
                branch=branch,
                processed_by=cashier,
                approved_by=approved_by,
                reason=reason,
                notes=notes,
                refund_amount=refund_total,
                refund_method=refund_method,
            )

            # ----------------------------------------------------------
            # 5. Create ReturnItems & restore stock
            # ----------------------------------------------------------
            for p in processed_items:
                ReturnItem.objects.create(
                    return_obj=return_obj,
                    sale_item=p['sale_item'],
                    quantity=p['quantity'],
                    unit_price=p['unit_price'],
                    line_total=p['line_total'],
                )

                # Restore stock (positive quantity = add back)
                StockService.adjust(
                    product=p['sale_item'].product,
                    branch=branch,
                    quantity=p['quantity'],
                    reason='return',
                    reference_id=return_number,
                    user=cashier,
                    batch=p['sale_item'].batch,
                    notes=f"Return from sale {original_sale.sale_number}",
                )

            # ----------------------------------------------------------
            # 6. Update original sale status
            # ----------------------------------------------------------
            # Check if ALL items are fully returned → 'refunded', else 'partial_refund'
            fully_returned = True
            for sale_item in original_sale.items.all():
                total_returned = (
                    ReturnItem.objects
                    .filter(sale_item=sale_item)
                    .aggregate(total=Sum('quantity'))['total']
                ) or Decimal('0.000')
                if total_returned < sale_item.quantity:
                    fully_returned = False
                    break

            original_sale.status = 'refunded' if fully_returned else 'partial_refund'
            original_sale.save()

            # ----------------------------------------------------------
            # 7. Audit log
            # ----------------------------------------------------------
            log_action(
                user=cashier,
                action='approve_return',
                model_name='Return',
                object_id=return_obj.id,
                branch=branch,
                after={
                    'return_number': return_number,
                    'refund_amount': float(refund_total),
                    'original_sale': original_sale.sale_number,
                    'approved_by': str(approved_by) if approved_by else None,
                },
            )

        return return_obj
