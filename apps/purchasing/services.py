from django.db import transaction
from apps.inventory.services import StockService

class GRNService:
    @staticmethod
    def receive(grn):
        with transaction.atomic():
            for item in grn.items.all():
                # 1. quantity_sale  (already computed by GRNItem.save())
                quantity_sale = item.quantity_sale_units
                
                # 2. StockService.adjust
                StockService.adjust(
                    product=item.product,
                    branch=grn.branch,
                    quantity=quantity_sale,
                    reason='purchase',
                    reference_id=grn.grn_number,
                    user=grn.received_by
                )
                
                # 3. Handle Expiry Date Batch
                if item.product.track_expiry and item.expiry_date:
                    from apps.products.models import ProductBatch
                    ProductBatch.objects.create(
                        product=item.product,
                        branch=grn.branch,
                        batch_number=item.batch_number,
                        expiry_date=item.expiry_date,
                        quantity_remaining=quantity_sale
                    )
                
                # 4. Update cost price
                product = item.product
                product.cost_price = item.cost_per_sale_unit
                product.save()
                
                # 5. PO link update
                if grn.purchase_order:
                    # In a real scenario we'd do a loop or query to get the specific PO item
                    po_items = grn.purchase_order.items.filter(product=item.product)
                    for po_item in po_items:
                        po_item.quantity_received_sale_units += quantity_sale
                        po_item.save()
            
            # 6. Check PO status updates
            if grn.purchase_order:
                po = grn.purchase_order
                all_received = True
                for po_item in po.items.all():
                    expected_sale_units = po_item.quantity_ordered * po_item.product.units_per_purchase
                    if po_item.quantity_received_sale_units < expected_sale_units:
                        all_received = False
                        break
                
                if all_received:
                    po.status = 'received'
                else:
                    po.status = 'partial'
                po.save()
