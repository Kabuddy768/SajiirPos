import pytest
from decimal import Decimal
from django.utils import timezone
from apps.inventory.services import StockService, InsufficientStockError
from apps.inventory.models import BranchStock, StockMovement
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
def test_stock_adjust_creates_movement_and_updates_branch_stock(db):
    from apps.products.models import Product, Category, Unit
    from apps.branches.models import Branch
    
    branch = Branch.objects.create(name="Test Branch")
    unit = Unit.objects.create(name="Piece", short_name="pc")
    cat = Category.objects.create(name="Test")
    user = User.objects.create_user(email="test@test.com", password="pwd")
    
    prod = Product.objects.create(name="Item 1", sku="123", category=cat, sale_unit=unit)
    
    # Check adjustment
    mov = StockService.adjust(
        product=prod,
        branch=branch,
        quantity=10,
        reason='opening',
        reference_id='REF-001',
        user=user
    )
    
    assert mov.quantity_before == Decimal('0.000')
    assert mov.quantity_after == Decimal('10.000')
    assert mov.reason == 'opening'
    
    # Reload branch stock (created by signal)
    bs = BranchStock.objects.get(product=prod, branch=branch)
    assert bs.quantity == Decimal('10.000')

@pytest.mark.django_db
def test_stock_adjust_insufficient_stock(db):
    from apps.products.models import Product, Category, Unit
    from apps.branches.models import Branch
    
    branch = Branch.objects.create(name="Test Branch")
    unit = Unit.objects.create(name="Piece", short_name="pc")
    cat = Category.objects.create(name="Test")
    user = User.objects.create_user(email="test@test.com", password="pwd")
    
    prod = Product.objects.create(name="Item 1", sku="123", category=cat, sale_unit=unit)
    
    # Start with 0. Subtracting should fail.
    with pytest.raises(InsufficientStockError):
        StockService.adjust(
            product=prod,
            branch=branch,
            quantity=-5,
            reason='sale',
            reference_id='REF-001',
            user=user
        )
