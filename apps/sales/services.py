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
    def _generate_sale_number(branch):
        date_str = timezone.localtime().strftime('%Y%m%d')
        unique_suffix = uuid.uuid4().hex[:6].upper()
        return f"{branch.etims_branch_code or 'BR'}-{date_str}-{unique_suffix}"

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
            
            if price != product.selling_price and not manager_override:
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
    def _create_payments(sale, payments):
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

    @staticmethod
    def _handle_loyalty_points(customer, total):
        if customer:
            points_earned = int(total // Decimal('100'))
            customer.loyalty_points += points_earned
            customer.save()

    @staticmethod
    def complete(cart, session_id, payments, cashier, customer, client_created_at, offline_uuid, schema_name, manager_override=False):
        """
        Complete a sale and its payments, ensuring idempotency via offline_uuid.
        """
        with transaction.atomic():
            session = SaleService._validate_session(session_id, cashier)
            
            existing_sale = Sale.objects.filter(offline_uuid=offline_uuid).first()
            if existing_sale:
                return existing_sale

            branch = session.branch
            sale_number = SaleService._generate_sale_number(branch)
            
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
                client_created_at=client_created_at,
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

            SaleService._create_payments(sale, payments)
            SaleService._handle_loyalty_points(customer, total)

            log_action(
                user=cashier,
                action='create',
                model_name='Sale',
                object_id=sale.id,
                branch=branch,
                after={'total': float(total), 'sale_number': sale_number}
            )

        if sale.pk:
            sign_sale_etims.delay(sale.pk, schema_name)
            
        return sale

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
                    reason='adjustment',
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

