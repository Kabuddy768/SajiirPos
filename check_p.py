import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pos_project.config.settings")
django.setup()
from django_tenants.utils import schema_context
from apps.products.models import Product
with schema_context("main"):
    p = Product.objects.filter(barcode="600123").first()
    if p:
        print(f"Product found: {p.name}, barcode: {p.barcode}, price: {p.selling_price}")
    else:
        print("Product NOT found in 'main' schema")
