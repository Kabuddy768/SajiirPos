from celery import shared_task
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from apps.sales.services import SaleService
from apps.products.models import Product
from apps.customers.models import Customer

User = get_user_model()

@shared_task
def process_mpesa_callback(data, schema_name):
    """
    Handles M-Pesa STK push callback.
    If successful, completes the sale using cached data.
    """
    stk_callback = data.get('Body', {}).get('stkCallback', {})
    if not stk_callback:
        return "Invalid callback data"

    checkout_id = stk_callback.get('CheckoutRequestID')
    result_code = stk_callback.get('ResultCode')
    
    if result_code == 0:
        offline_uuid = cache.get(f"mpesa_checkout_{checkout_id}")
        if not offline_uuid:
            return f"No offline_uuid found for checkout_id {checkout_id}"
            
        sale_data = cache.get(f"pending_sale_{offline_uuid}")
        if not sale_data:
            return f"No sale data found for offline_uuid {offline_uuid}"

        with schema_context(schema_name):
            try:
                # Reconstruct cart with actual product objects
                cart = []
                for item in sale_data['cart']:
                    product = Product.objects.get(id=item['product_id'])
                    cart_item = dict(item)
                    cart_item['product'] = product
                    cart_item['batch'] = None # Batch handling could be added here
                    cart.append(cart_item)
                
                cashier = User.objects.get(id=sale_data['cashier_id'])
                customer = None
                if sale_data.get('customer_id'):
                    customer = Customer.objects.filter(id=sale_data['customer_id']).first()
                    
                SaleService.complete(
                    cart=cart,
                    session_id=sale_data['session_id'],
                    payments=sale_data['payments'],
                    cashier=cashier,
                    customer=customer,
                    client_created_at=sale_data['client_created_at'],
                    offline_uuid=sale_data['offline_uuid'],
                    schema_name=schema_name,
                    manager_override=sale_data.get('manager_override', False)
                )
                return f"Sale {offline_uuid} completed successfully via M-Pesa callback"
            except Exception as e:
                return f"Error completing sale {offline_uuid}: {str(e)}"
    else:
        result_desc = stk_callback.get('ResultDesc', 'Unknown error')
        return f"M-Pesa payment failed for {checkout_id}: {result_desc} (Code: {result_code})"
