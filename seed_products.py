import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_project.config.settings')
django.setup()

from django_tenants.utils import schema_context
from apps.products.models import Category, Unit, Product
from apps.accounts.models import CustomUser

def seed():
    with schema_context('main'):
        admin = CustomUser.objects.filter(email='admin@pos.com').first()
        if not admin:
            print("Admin user not found. Please run setup_pos.py first.")
            return
            
        # 1. Categories
        cat_food, _ = Category.objects.get_or_create(name='Food & Beverage')
        cat_elec, _ = Category.objects.get_or_create(name='Electronics')
        
        # 2. Units
        u_pcs, _ = Unit.objects.get_or_create(name='Pieces', short_name='pcs')
        u_kg, _ = Unit.objects.get_or_create(name='Kilograms', short_name='kg')
        
        # 3. Products
        products = [
            {
                'name': 'Soda 500ml',
                'sku': 'SOD-500',
                'barcode': '600123',
                'category': cat_food,
                'selling_price': 70.00,
                'cost_price': 55.00,
                'sale_unit': u_pcs,
                'tax_type': 'V'
            },
            {
                'name': 'Bread 400g',
                'sku': 'BRD-400',
                'barcode': '600456',
                'category': cat_food,
                'selling_price': 65.00,
                'cost_price': 50.00,
                'sale_unit': u_pcs,
                'tax_type': 'Z'
            },
            {
                'name': 'USB Cable 1m',
                'sku': 'USB-1M',
                'barcode': '700789',
                'category': cat_elec,
                'selling_price': 250.00,
                'cost_price': 150.00,
                'sale_unit': u_pcs,
                'tax_type': 'V'
            }
        ]
        
        from apps.inventory.services import StockService
        from apps.branches.models import Branch
        branch = Branch.objects.first()
        
        for p_data in products:
            p, created = Product.objects.get_or_create(
                sku=p_data['sku'],
                defaults={
                    'name': p_data['name'],
                    'barcode': p_data['barcode'],
                    'category': p_data['category'],
                    'selling_price': p_data['selling_price'],
                    'cost_price': p_data['cost_price'],
                    'sale_unit': p_data['sale_unit'],
                    'tax_type': p_data['tax_type'],
                    'created_by': admin
                }
            )
            if created:
                print(f"Created product: {p.name}")
                # Add initial stock
                StockService.adjust(
                    product=p,
                    branch=branch,
                    quantity=100,
                    reason='initial_stock',
                    reference_id='SEED-001',
                    user=admin
                )
                print(f"Added 100 units of stock for {p.name}")
            else:
                print(f"Product already exists: {p.name}")

if __name__ == '__main__':
    seed()
