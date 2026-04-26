import pytest
from decimal import Decimal
from django.utils import timezone
import uuid
from apps.sales.services import SaleService, SessionClosedError
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
def test_sale_service_complete(db, mocker):
    mocker.patch('workers.etims_tasks.sign_sale_etims.delay')
    
    from apps.products.models import Product, Category, Unit
    from apps.branches.models import Branch
    from apps.sales.models import CashSession, Sale
    from apps.inventory.services import StockService
    
    branch = Branch.objects.create(name="Test Branch", etims_branch_code="B1")
    unit = Unit.objects.create(name="Piece", short_name="pc")
    cat = Category.objects.create(name="Test")
    user = User.objects.create_user(email="test@test.com", password="pwd")
    
    prod = Product.objects.create(name="Item 1", sku="123", category=cat, sale_unit=unit, cost_price=Decimal('50'), tax_type='V', is_tax_inclusive=True)
    
    # Pre-stock
    StockService.adjust(product=prod, branch=branch, quantity=10, reason='opening', reference_id='OPEN', user=user)
    
    session = CashSession.objects.create(branch=branch, cashier=user, status='open')
    
    cart = [
        {
            'product': prod,
            'quantity': Decimal('2'),
            'unit_price': Decimal('100.00'),
            'discount_amount': Decimal('0.00')
        }
    ]
    
    payments = [
        {'method': 'cash', 'amount': Decimal('200.00')}
    ]
    
    offline_uuid = uuid.uuid4()
    
    sale = SaleService.complete(
        cart=cart,
        session_id=session.id,
        payments=payments,
        cashier=user,
        customer=None,
        client_created_at=timezone.now(),
        offline_uuid=offline_uuid,
        schema_name="public"
    )
    
    assert sale.sale_number.startswith("B1-")
    assert sale.total_amount == Decimal('200.00')
    assert sale.status == 'completed'
    
    # Verify stock deducted
    from apps.inventory.models import BranchStock
    bs = BranchStock.objects.get(product=prod, branch=branch)
    assert bs.quantity == Decimal('8.000')

@pytest.mark.django_db
def test_sale_service_idempotence(db):
    from apps.products.models import Product, Category, Unit
    from apps.branches.models import Branch
    from apps.sales.models import CashSession, Sale
    
    branch = Branch.objects.create(name="Test Branch")
    user = User.objects.create_user(email="test@test.com", password="pwd")
    session = CashSession.objects.create(branch=branch, cashier=user, status='open')
    
    offline_uuid = uuid.uuid4()
    # Create the sale manually first to mimic existing entry
    Sale.objects.create(
        sale_number="DUP",
        session=session,
        branch=branch,
        cashier=user,
        client_created_at=timezone.now(),
        offline_uuid=offline_uuid
    )
    
    # Call service with same UUID
    sale = SaleService.complete(
        cart=[],
        session_id=session.id,
        payments=[],
        cashier=user,
        customer=None,
        client_created_at=timezone.now(),
        offline_uuid=offline_uuid,
        schema_name="public"
    )
    
    # Should just return the duplicate sale
    assert sale.sale_number == "DUP"
