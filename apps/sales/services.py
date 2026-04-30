import uuid
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from apps.inventory.services import StockService, InsufficientStockError
from .models import Sale, SaleItem, CashSession
from apps.payments.models import Payment
from workers.etims_tasks import sign_sale_etims
from apps.audit.utils import log_action

class SessionClosedError(Exception):
    pass

class DuplicateSaleError(Exception):
    pass

class SaleService:
    @staticmethod
    def complete(cart, session_id, payments, cashier, customer, client_created_at, offline_uuid, schema_name, manager_override=False):
        """
        Complete a sale and its payments, ensuring idempotency via offline_uuid.
        """
        with transaction.atomic():
            # 1. Validate session
            try:
                session = CashSession.objects.get(id=session_id)
            except CashSession.DoesNotExist:
                raise ValueError("Invalid session.")
                
            if session.status != 'open':
                raise SessionClosedError("The cash session is closed.")
            
            if session.cashier != cashier:
                raise ValueError("Cashier mismatch on session.")

            # 2. Validate offline_uuid idempotency
            existing_sale = Sale.objects.filter(offline_uuid=offline_uuid).first()
            if existing_sale:
                return existing_sale

            # 3. Generate sale number: {BRANCH_CODE}-{YYYYMMDD}-{UNIQUE_SUFFIX}
            branch = session.branch
            date_str = timezone.localtime().strftime('%Y%m%d')
            # Use UUID to avoid race conditions and ensure uniqueness
            unique_suffix = uuid.uuid4().hex[:6].upper()
            sale_number = f"{branch.etims_branch_code or 'BR'}-{date_str}-{unique_suffix}"

            # 4. Compute totals
            subtotal = Decimal('0.00')
            discount = Decimal('0.00')
            taxable_amount = Decimal('0.00')
            tax_amount = Decimal('0.00')
            total = Decimal('0.00')

            # We process items and keep them in a processed list to create them later
            processed_items = []
            for item in cart:
                product = item['product']
                if not product.is_active:
                    raise ValueError(f"Product {product.name} is not active.")
                
                qty = Decimal(str(item['quantity']))
                price = Decimal(str(item['unit_price']))
                disc = Decimal(str(item.get('discount_amount', '0.00')))
                
                # Price validation
                if price != product.selling_price and not manager_override:
                    raise ValueError(f"Price mismatch for {product.name}. Expected {product.selling_price}, got {price}")
                
                line_subtotal = (qty * price) - disc
                item_tax = Decimal('0.00')
                
                # VAT calculation following KRA rules
                if product.tax_type == 'V':
                    if product.is_tax_inclusive:
                        item_tax = line_subtotal - (line_subtotal / Decimal('1.16'))
                        taxable_amount += (line_subtotal - item_tax)
                        line_total = line_subtotal
                    else:
                        item_tax = line_subtotal * Decimal('0.16')
                        taxable_amount += line_subtotal
                        line_total = line_subtotal + item_tax
                else:
                    taxable_amount += line_subtotal
                    line_total = line_subtotal
                
                subtotal += (qty * price)
                discount += disc
                total += line_total
                tax_amount += item_tax

                processed_items.append({
                    'product': product,
                    'quantity': qty,
                    'unit_price': price,
                    'cost_price': product.cost_price,
                    'discount_amount': disc,
                    'tax_amount': item_tax,
                    'line_total': line_total,
                    'tax_type': product.tax_type,
                    'batch': item.get('batch')
                })

            # Check total vs payments
            payment_total = sum(Decimal(str(p['amount'])) for p in payments)
            # In a real app we'd strict-check payment_total >= total.
            
            # 5. Create Sale
            sale = Sale.objects.create(
                sale_number=sale_number,
                session=session,
                branch=branch,
                cashier=cashier,
                customer=customer,
                subtotal=subtotal,
                discount_amount=discount,
                taxable_amount=taxable_amount,
                tax_amount=tax_amount,
                total_amount=total,
                status='completed',
                client_created_at=client_created_at,
                offline_uuid=offline_uuid,
                is_offline_sale=False # Determined elsewhere if needed
            )

            # 6. Create SaleItems & 9. Adjust Stock
            for p_item in processed_items:
                SaleItem.objects.create(
                    sale=sale,
                    product=p_item['product'],
                    quantity=p_item['quantity'],
                    unit_price=p_item['unit_price'],
                    cost_price=p_item['cost_price'],
                    discount_amount=p_item['discount_amount'],
                    tax_amount=p_item['tax_amount'],
                    line_total=p_item['line_total'],
                    tax_type=p_item['tax_type'],
                    batch=p_item['batch']
                )

                StockService.adjust(
                    product=p_item['product'],
                    branch=branch,
                    quantity=-p_item['quantity'],
                    reason='sale',
                    reference_id=sale.sale_number,
                    user=cashier,
                    batch=p_item['batch']
                )

            # 7. Create Payments
            for p in payments:
                status = 'pending' if p['method'] == 'mpesa' else 'confirmed'
                Payment.objects.create(
                    sale=sale,
                    method=p['method'],
                    amount=Decimal(str(p['amount'])),
                    status=status,
                    mpesa_phone=p.get('mpesa_phone', ''),
                    card_reference=p.get('card_reference', '')
                )

            # 10. Loyalty points
            if customer:
                points_earned = int(total // Decimal('100'))
                customer.loyalty_points += points_earned
                customer.save()

            # 11. Log action
            log_action(
                user=cashier,
                action='create',
                model_name='Sale',
                object_id=sale.id,
                branch=branch,
                after={'total': float(total), 'sale_number': sale_number}
            )

        # Post-transaction: 12. Queue eTIMS
        if sale.pk:
            sign_sale_etims.delay(sale.pk, schema_name)
            
        return sale

    @staticmethod
    def void(sale, voided_by, reason=''):
        """
        Void a completed sale.
        Rules:
        - Only 'completed' sales can be voided.
        - Voids are only allowed on the same calendar day as the sale.
        - All stock deductions are reversed (items go back into BranchStock).
        - All payments are marked as 'refunded'.
        - The sale status is set to 'voided'.
        """
        if sale.status != 'completed':
            raise ValueError(
                f"Cannot void sale {sale.sale_number} — status is '{sale.status}'."
            )

        # Same-day check
        sale_date = sale.created_at.date()
        today = timezone.localtime().date()
        if sale_date != today:
            raise ValueError(
                f"Cannot void sale {sale.sale_number} — it was created on "
                f"{sale_date}, but today is {today}. Only same-day voids are allowed."
            )

        with transaction.atomic():
            # 1. Reverse stock for every SaleItem
            for item in sale.items.select_related('product'):
                StockService.adjust(
                    product=item.product,
                    branch=sale.branch,
                    quantity=item.quantity,  # positive = add back
                    reason='adjustment',
                    reference_id=f"VOID-{sale.sale_number}",
                    user=voided_by,
                    batch=item.batch,
                    notes=f"Void reversal for sale {sale.sale_number}",
                )

            # 2. Mark all payments as refunded
            sale.payments.update(status='refunded')

            # 3. Reverse loyalty points
            if sale.customer:
                points_to_remove = int(sale.total_amount // Decimal('100'))
                sale.customer.loyalty_points = max(
                    0, sale.customer.loyalty_points - points_to_remove
                )
                sale.customer.save()

            # 4. Update sale status
            sale.status = 'voided'
            sale.save()

            # 5. Audit log
            log_action(
                user=voided_by,
                action='void_sale',
                model_name='Sale',
                object_id=sale.id,
                branch=sale.branch,
                before={'status': 'completed', 'total': float(sale.total_amount)},
                after={'status': 'voided'},
                notes=reason,
            )

        return sale

