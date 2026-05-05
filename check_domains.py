import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pos_project.config.settings")
django.setup()
from apps.tenants.models import Domain
for d in Domain.objects.all():
    print(f"Domain: {d.domain}, tenant: {d.tenant.schema_name}")
