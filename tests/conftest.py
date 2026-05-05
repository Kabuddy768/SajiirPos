import pytest
from apps.tenants.models import Tenant, Domain
from django.contrib.auth import get_user_model
from apps.branches.models import Branch
from apps.sales.models import CashSession
from apps.products.models import Product, Category, Unit

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
def category(tenant):
    return Category.objects.create(name='Test Category')

@pytest.fixture
def sale_unit(tenant):
    return Unit.objects.create(name='Piece', short_name='pc')

@pytest.fixture
def product(tenant, category, sale_unit, user):
    p = Product(
        name='Test Product', barcode='123456789', sku='123456789',
        selling_price=100, cost_price=50, is_active=True, tax_type='V',
        category=category, sale_unit=sale_unit, created_by=user
    )
    p.full_clean()
    p.save()
    return p
