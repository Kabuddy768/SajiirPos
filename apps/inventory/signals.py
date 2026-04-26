from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from .models import StockMovement, BranchStock

@receiver(post_save, sender=StockMovement)
def update_branch_stock(sender, instance, created, **kwargs):
    if created:
        with transaction.atomic():
            branch_stock, _ = BranchStock.objects.select_for_update().get_or_create(
                product=instance.product,
                branch=instance.branch,
                defaults={'quantity': 0}
            )
            branch_stock.quantity = instance.quantity_after
            branch_stock.save()
