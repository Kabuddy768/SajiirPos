from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, F
from apps.sales.models import SaleItem
from apps.inventory.models import ProductBatch
from apps.purchasing.models import PurchaseOrder, PurchaseOrderItem, Supplier
from apps.products.models import Product
from apps.branches.models import Branch
import logging

logger = logging.getLogger(__name__)

@shared_task
def generate_demand_based_po():
    """
    Analyzes last 14 days of sales to forecast demand and draft POs for low stock SKUs.
    This runs daily.
    """
    days_to_analyze = 14
    cutoff = timezone.now() - timedelta(days=days_to_analyze)
    
    # Calculate daily average sales per product per branch
    sales_data = SaleItem.objects.filter(
        sale__created_at__gte=cutoff,
        sale__status='completed'
    ).values('product', 'sale__branch').annotate(
        total_sold=Sum('quantity')
    )
    
    forecasts = {}
    for entry in sales_data:
        daily_avg = entry['total_sold'] / days_to_analyze
        forecasts[(entry['product'], entry['sale__branch'])] = daily_avg

    branches = Branch.objects.all()
    po_count = 0
    
    for branch in branches:
        # Dictionary to keep track of draft POs per supplier for this branch
        branch_pos = {}
        
        # Check all active products
        products = Product.objects.filter(is_active=True).select_related('primary_supplier')
        
        for prod in products:
            avg_daily_sale = forecasts.get((prod.id, branch.id), 0)
            
            # Lead time + safety stock logic
            lead_time_days = 3
            safety_days = 4
            reorder_threshold = avg_daily_sale * (lead_time_days + safety_days)
            
            # Use minimum_stock_level as a floor if demand is very low
            effective_threshold = max(reorder_threshold, prod.minimum_stock_level)
            
            if effective_threshold <= 0:
                continue

            # Current stock across all batches in this branch
            current_stock = ProductBatch.objects.filter(
                product=prod, branch=branch
            ).aggregate(total=Sum('quantity_remaining'))['total'] or 0
            
            if current_stock < effective_threshold:
                supplier = prod.primary_supplier
                if not supplier:
                    logger.warning(f"Product {prod.name} needs reorder but has no primary supplier.")
                    continue
                
                # Check if we already have a draft PO for this supplier/branch
                if supplier.id not in branch_pos:
                    po_num = f"AUTO-{branch.id}-{timezone.now().strftime('%y%m%d%H%M')}"
                    po = PurchaseOrder.objects.create(
                        order_number=po_num,
                        supplier=supplier,
                        branch=branch,
                        status='draft',
                        notes="Auto-generated PO based on 14-day sales velocity.",
                        created_by=None
                    )
                    branch_pos[supplier.id] = po
                    po_count += 1
                
                po = branch_pos[supplier.id]
                
                # Calculate reorder quantity (e.g., 2 weeks of stock)
                reorder_qty = (avg_daily_sale * 14) or prod.reorder_quantity
                
                # Create PO Item
                PurchaseOrderItem.objects.create(
                    order=po,
                    product=prod,
                    quantity_ordered=reorder_qty,
                    purchase_unit=prod.purchase_unit or prod.sale_unit,
                    unit_cost=prod.cost_price
                )
                
    return po_count
