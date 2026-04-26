import pytest
from apps.tenants.models import Tenant, Domain
from django.contrib.auth import get_user_model
from apps.branches.models import Branch
from apps.sales.models import CashSession
from apps.products.models import Product

User = get_user_model()

@pytest.fixture
def tenant(db):
    tenant = Tenant.objects.create(schema_name='test_schema', name='Test Tenant')
    Domain.objects.create(domain='test.localhost', tenant=tenant, is_primary=True)
    return tenant

@pytest.fixture
def branch(tenant):
    return Branch.objects.create(name='Main Branch')

@pytest.fixture
def user(tenant):
    return User.objects.create_user(username='testuser', email='test@test.com', password='password')

@pytest.fixture
def session(branch, user):
    return CashSession.objects.create(branch=branch, cashier=user, opening_float=100)

@pytest.fixture
def product(tenant):
    return Product.objects.create(name='Test Product', barcode='123456789', price=100, cost_price=50, is_active=True, tax_type='V')
