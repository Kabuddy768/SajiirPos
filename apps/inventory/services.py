from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from .models import BranchStock, StockMovement

class InsufficientStockError(Exception):
    pass

class StockService:
    @staticmethod
    def adjust(product, branch, quantity, reason, reference_id, user, batch=None, notes=''):
        """
        Adjust stock by creating a StockMovement.
        The actual BranchStock is updated via a post_save signal on StockMovement.
        """
        with transaction.atomic():
            branch_stock, created = BranchStock.objects.select_for_update().get_or_create(
                product=product,
                branch=branch,
                defaults={'quantity': Decimal('0.000')}
            )
            
            quantity_before = branch_stock.quantity
            quantity_after = quantity_before + Decimal(str(quantity))
            
            if quantity_after < 0:
                raise InsufficientStockError(f"Insufficient stock for {product.name}. Cannot subtract {-quantity}.")

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

            return movement
