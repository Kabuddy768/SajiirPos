from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import StockMovement

# Redundant signal removed: StockService.adjust now handles BranchStock updates directly
# to avoid race conditions and double-locking.
