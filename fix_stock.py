import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pos_project.config.settings")
django.setup()
from django_tenants.utils import schema_context
from apps.products.models import Product
from apps.inventory.services import StockService
from apps.branches.models import Branch
from apps.accounts.models import CustomUser
with schema_context("main"):
    branch = Branch.objects.first()
    admin = CustomUser.objects.get(email="admin@pos.com")
    for p in Product.objects.all():
        StockService.adjust(product=p, branch=branch, quantity=100, reason="initial_stock", reference_id="SEED-FIX-2", user=admin)
        print(f"Added 100 stock for {p.name}")
