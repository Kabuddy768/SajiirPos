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
    def _validate_session(session_id, cashier):
        try:
            session = CashSession.objects.get(id=session_id)
        except CashSession.DoesNotExist:
            raise ValueError("Invalid session.")
            
        if session.status != 'open':
            raise SessionClosedError("The cash session is closed.")
        
        if session.cashier != cashier:
            raise ValueError("Cashier mismatch on session.")
            
        return session

    @staticmethod
    def _generate_sale_number(branch, date_str=None):
        """
        Generate a KRA-compliant sequential sale number atomically.
        Format: {BRANCH_CODE}-{YYYYMMDD}-{SEQUENCE:05d}
        MUST be called inside an existing transaction.atomic() block — the
        counter increment rolls back with the sale if creation fails.
        """
        if not date_str:
            date_str = timezone.localtime().strftime('%Y%m%d')
        
        prefix = f"{branch.etims_branch_code or 'BR'}-{date_str}"

        from apps.sales.models import DailySaleCounter
        # select_for_update() serialises concurrent calls; the outer transaction
        # guarantees the increment rolls back if Sale.objects.create() later fails.
        counter, _ = DailySaleCounter.objects.select_for_update().get_or_create(
            branch=branch,
            date_str=date_str,
            defaults={'counter': 0}
        )
        counter.counter += 1
        counter.save()
        return f"{prefix}-{counter.counter:05d}"


    @staticmethod
    def _process_cart(cart, manager_override):
        subtotal = Decimal('0.00')
        discount = Decimal('0.00')
        taxable_amount = Decimal('0.00')
        tax_amount = Decimal('0.00')
        total = Decimal('0.00')
        processed_items = []

        for item in cart:
            product = item['product']
            if not product.is_active:
                raise ValueError(f"Product {product.name} is not active.")
            
            qty = Decimal(str(item['quantity']))
            price = Decimal(str(item['unit_price']))
            disc = Decimal(str(item.get('discount_amount', '0.00')))
            
            if disc > 0 and not product.allow_discount:
                raise ValueError(f"Discounts are not allowed for {product.name}")

            # Use quantize to handle floating point drift (rounding to 2 decimal places)
            if price.quantize(Decimal('0.01')) != product.selling_price.quantize(Decimal('0.01')) and not manager_override:
                raise ValueError(f"Price mismatch for {product.name}. Expected {product.selling_price}, got {price}")
            
            line_subtotal = (qty * price) - disc
            item_tax = Decimal('0.00')
            
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

        return processed_items, subtotal, discount, taxable_amount, tax_amount, total

    @staticmethod
    def _create_payments(sale, payments, customer):
        for p in payments:
            status = 'pending' if p['method'] == 'mpesa' else 'confirmed'
            amt = Decimal(str(p['amount']))
            
            if p['method'] == 'points':
                if not customer:
                    raise ValueError("Points payment requires a customer profile.")
                
                # 1 Point = 1 KES conversion
                points_needed = int(amt)
                if customer.loyalty_points < points_needed:
                    raise ValueError(f"Insufficient loyalty points. Have {customer.loyalty_points}, need {points_needed}.")
                
                # Ensure points payment doesn't exceed the sale total
                # (prevent a KES 5,000 sale being paid with 50 points by passing amount=5000)
                total_paid_by_other_methods = sum(
                    Decimal(str(other['amount'])) for other in payments if other['method'] != 'points'
                )
                remaining_balance = sale.total_amount - total_paid_by_other_methods
                if amt > remaining_balance:
                    raise ValueError(
                        f"Points payment of KES {amt} exceeds remaining balance of KES {remaining_balance}. "
                        f"Reduce the points amount or add another payment method to cover the full total."
                    )
                
                customer.loyalty_points -= points_needed
                customer.save()
                status = 'confirmed'

            elif p['method'] == 'store_credit':
                if not customer:
                    raise ValueError("Store credit payment requires a customer profile.")
                if not customer.allow_credit_sales:
                    raise ValueError(f"Credit sales are not allowed for customer {customer.name}.")
                
                # Check credit limit
                available_credit = customer.credit_limit - customer.current_credit_balance
                if amt > available_credit:
                    raise ValueError(
                        f"Credit limit exceeded. Customer has KES {available_credit:.2f} available credit, "
                        f"but this payment requires KES {amt:.2f}."
                    )
                
                customer.current_credit_balance += amt
                customer.save()
                
                # Record ledger entry
                from apps.customers.models import CustomerCreditLedger
                CustomerCreditLedger.objects.create(
                    customer=customer,
                    sale=sale,
                    transaction_type=CustomerCreditLedger.TYPE_CHARGE,
                    amount=amt,
                    recorded_by=sale.cashier,
                    notes=f"Store credit charge for sale {sale.sale_number}."
                )
                status = 'confirmed'

            Payment.objects.create(
                sale=sale,
                method=p['method'],
                amount=amt,
                status=status,
                mpesa_phone=p.get('mpesa_phone') or '',
                card_reference=p.get('card_reference') or '',
            )

    @staticmethod

    def _handle_loyalty_points(customer, total):
        if customer:
            from apps.customers.models import LoyaltyTier
            points_earned = int(total // Decimal('100'))
            customer.loyalty_points += points_earned
            customer.last_purchase_at = timezone.now()
            
            # Auto-update tier based on points
            best_tier = LoyaltyTier.objects.filter(
                min_points__lte=customer.loyalty_points
            ).order_by('-min_points').first()
            
            if best_tier:
                customer.tier = best_tier
                
            customer.save()

    @staticmethod
    def complete(cart, session_id, payments, cashier, customer, client_created_at, offline_uuid, schema_name, manager_override=False):
        """
        Complete a sale and its payments, ensuring idempotency via offline_uuid.
        """
        import logging
        import datetime
        logger = logging.getLogger(__name__)

        try:
            with transaction.atomic():
                session = SaleService._validate_session(session_id, cashier)
                
                # Validation: Backdating window (max 7 days)
                if isinstance(client_created_at, str):
                    client_time = timezone.datetime.fromisoformat(client_created_at.replace('Z', '+00:00'))
                else:
                    client_time = client_created_at or timezone.now()

                if client_time < timezone.now() - datetime.timedelta(days=7):
                    raise ValueError("Sale date is too far in the past. Maximum 7 days for offline sync.")
                if client_time > timezone.now() + datetime.timedelta(minutes=30):
                    raise ValueError("Sale date cannot be in the future.")

                # Check idempotency
                existing_sale = Sale.objects.filter(offline_uuid=offline_uuid).first()
                if existing_sale:
                    return existing_sale

                branch = session.branch
                
                # Generate sale number (using client_created_at date if provided for consistency)
                date_prefix = client_time.strftime('%Y%m%d')
                sale_number = SaleService._generate_sale_number(branch, date_str=date_prefix)
                
                processed_items, subtotal, discount, taxable_amount, tax_amount, total = SaleService._process_cart(cart, manager_override)

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
                    client_created_at=client_time,
                    offline_uuid=offline_uuid,
                    is_offline_sale=False
                )

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

                SaleService._create_payments(sale, payments, customer)
                SaleService._handle_loyalty_points(customer, total)

                log_action(
                    user=cashier,
                    action='create',
                    model_name='Sale',
                    object_id=sale.id,
                    branch=branch,
                    after={'total': float(total), 'sale_number': sale_number}
                )

            # Trigger background task outside transaction
            if sale.pk:
                try:
                    from workers.etims_tasks import sign_sale_etims
                    sign_sale_etims.apply_async(args=[sale.pk, schema_name], retry=False)
                except Exception as task_err:
                    logger.error(f"Failed to queue sign_sale_etims background task: {str(task_err)}")
                
            return sale

        except Exception as e:
            logger.exception(f"Sale completion failed for UUID {offline_uuid}: {str(e)}")
            raise e

    @staticmethod
    def void(sale, voided_by, reason=''):
        """
        Void a completed sale.
        """
        if sale.status != 'completed':
            raise ValueError(f"Cannot void sale {sale.sale_number} — status is '{sale.status}'.")

        sale_date = sale.created_at.date()
        today = timezone.localtime().date()
        if sale_date != today:
            raise ValueError(
                f"Cannot void sale {sale.sale_number} — it was created on "
                f"{sale_date}, but today is {today}. Only same-day voids are allowed."
            )

        with transaction.atomic():
            for item in sale.items.select_related('product'):
                StockService.adjust(
                    product=item.product,
                    branch=sale.branch,
                    quantity=item.quantity,
                    reason='return',
                    reference_id=f"VOID-{sale.sale_number}",
                    user=voided_by,
                    batch=item.batch,
                    notes=f"Void reversal for sale {sale.sale_number}",
                )

            sale.payments.update(status='refunded')

            if sale.customer:
                points_to_remove = int(sale.total_amount // Decimal('100'))
                sale.customer.loyalty_points = max(0, sale.customer.loyalty_points - points_to_remove)
                sale.customer.save()

            sale.status = 'voided'
            sale.save()

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

