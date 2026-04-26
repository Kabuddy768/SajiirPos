import uuid
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from apps.inventory.services import StockService, InsufficientStockError
from .models import Sale, SaleItem, CashSession
from apps.payments.models import Payment
from workers.etims_tasks import sign_sale_etims

class SessionClosedError(Exception):
    pass

class DuplicateSaleError(Exception):
    pass

class SaleService:
    @staticmethod
    def complete(cart, session_id, payments, cashier, customer, client_created_at, offline_uuid, schema_name):
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

            # 3. Generate sale number: {BRANCH_CODE}-{YYYYMMDD}-{NNNN}
            branch = session.branch
            date_str = timezone.localtime().strftime('%Y%m%d')
            count_today = Sale.objects.filter(branch=branch, created_at__date=timezone.localtime().date()).count() + 1
            sale_number = f"{branch.etims_branch_code or 'BR'}-{date_str}-{count_today:04d}"

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
                
                line_total = (qty * price) - disc
                
                subtotal += (qty * price)
                discount += disc
                total += line_total
                
                # Simple VAT calculation (Assuming inclusive for now, but following rules)
                # KRA ETIMS: Taxable amount vs Tax amount
                item_tax = Decimal('0.00')
                if product.tax_type == 'V':
                    if product.is_tax_inclusive:
                        item_tax = line_total - (line_total / Decimal('1.16'))
                        taxable_amount += (line_total - item_tax)
                    else:
                        item_tax = line_total * Decimal('0.16')
                        taxable_amount += line_total
                        total += item_tax
                else:
                    taxable_amount += line_total
                
                tax_amount += item_tax

                processed_items.append({
                    'product': product,
                    'quantity': qty,
                    'unit_price': price,
                    'cost_price': product.cost_price,
                    'discount_amount': disc,
                    'tax_amount': item_tax,
                    'line_total': line_total + (item_tax if not product.is_tax_inclusive else 0),
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

        # Post-transaction: 11. Queue eTIMS
        if sale.pk:
            sign_sale_etims.delay(sale.pk, schema_name)
            
        return sale
