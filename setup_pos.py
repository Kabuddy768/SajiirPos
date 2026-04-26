import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_project.config.settings')
django.setup()

from apps.tenants.models import Tenant, Domain
from django.contrib.auth import get_user_model

User = get_user_model()

def setup():
    # 1. Create Public Tenant
    if not Tenant.objects.filter(schema_name='public').exists():
        public = Tenant.objects.create(
            schema_name='public',
            name='Sajiir POS Admin',
            is_active=True
        )
        Domain.objects.create(
            domain='localhost',
            tenant=public,
            is_primary=True
        )
        print("Public tenant created.")
    else:
        print("Public tenant already exists.")

    # 2. Create Main Store Tenant
    if not Tenant.objects.filter(schema_name='main').exists():
        store = Tenant.objects.create(
            schema_name='main',
            name='Main Store Branch',
            is_active=True
        )
        Domain.objects.create(
            domain='main.localhost',
            tenant=store,
            is_primary=True
        )
        print("Main store tenant created.")
    else:
        print("Main store tenant already exists.")

    # 3. Create Superuser (in public)
    if not User.objects.filter(email='admin@pos.com').exists():
        User.objects.create_superuser(
            email='admin@pos.com',
            password='admin123',
            first_name='Admin',
            last_name='User'
        )
        print("Superuser admin@pos.com created with password: admin123")
    else:
        print("Superuser already exists.")

if __name__ == '__main__':
    setup()
