from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from .models import BranchStock, StockMovement

from apps.audit.utils import log_action

class InsufficientStockError(Exception):
    pass

class StockService:
    @staticmethod
    def adjust(product, branch, quantity, reason, reference_id, user, batch=None, notes=''):
        """
        Adjust stock by creating a StockMovement and updating BranchStock/Batch.
        """
        with transaction.atomic():
            branch_stock, created = BranchStock.objects.select_for_update().get_or_create(
                product=product,
                branch=branch,
                defaults={'quantity': Decimal('0.000')}
            )
            
            quantity_before = branch_stock.quantity
            quantity_delta = Decimal(str(quantity))
            quantity_after = quantity_before + quantity_delta
            
            if quantity_after < 0:
                raise InsufficientStockError(f"Insufficient stock for {product.name}. Current: {quantity_before}, requested: {quantity}.")

            # Update BranchStock directly
            branch_stock.quantity = quantity_after
            branch_stock.save()

            # Update Batch if provided — re-fetch with lock to avoid race conditions
            if batch:
                from apps.products.models import ProductBatch
                locked_batch = ProductBatch.objects.select_for_update().get(pk=batch.pk)
                locked_batch.quantity_remaining += quantity_delta
                locked_batch.save()

            movement = StockMovement.objects.create(
                product=product,
                branch=branch,
                reason=reason,
                quantity=quantity,
                quantity_before=quantity_before,
                quantity_after=quantity_after,
                unit_cost=product.cost_price,
                notes=notes,
                reference_id=reference_id,
                batch=batch,
                performed_by=user
            )

            # Log the action
            log_action(
                user=user,
                action='adjust_stock',
                model_name='StockMovement',
                object_id=movement.id,
                branch=branch,
                before={'quantity': float(quantity_before)},
                after={'quantity': float(quantity_after)},
                notes=f"Reason: {reason}, Ref: {reference_id}"
            )

            return movement

