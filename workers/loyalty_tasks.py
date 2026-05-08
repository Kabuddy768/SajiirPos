from celery import shared_task
from django.utils import timezone
from django.db.models import Q
from django_tenants.utils import schema_context
import datetime
import africastalking
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

@shared_task
def detect_churned_customers(schema_name):
    """
    Find customers who haven't made a purchase in 30 days and send a re-engagement SMS.
    schema_name must be passed by the Celery Beat schedule or the calling code.
    """
    # Initialize Africa's Talking outside schema_context (no DB needed)
    try:
        africastalking.initialize(
            settings.AFRICASTALKING_USERNAME,
            settings.AFRICASTALKING_API_KEY
        )
        sms = africastalking.SMS
    except Exception as e:
        logger.error(f"Failed to initialize Africa's Talking: {str(e)}")
        return 0

    churn_threshold_days = 30
    cutoff_date = timezone.now() - datetime.timedelta(days=churn_threshold_days)

    with schema_context(schema_name):
        from apps.customers.models import Customer

        # Get active customers who haven't bought since the cutoff date
        # Or haven't bought at all but were created 30 days ago
        churned_customers = Customer.objects.filter(
            is_active=True,
            phone__isnull=False
        ).filter(
            Q(last_purchase_at__lt=cutoff_date) | 
            Q(last_purchase_at__isnull=True, created_at__lt=cutoff_date)
        ).exclude(phone='')
        
        sent_count = 0
        for customer in churned_customers:
            # Create a unique discount code
            discount_code = f"BACK10-{customer.id}"
            message = f"Hello {customer.name}, we miss you at Sajiir POS! Visit us soon and use code {discount_code} for 10% off."
            
            try:
                phone = str(customer.phone).strip()
                if phone.startswith('0'):
                    phone = '254' + phone[1:]
                elif not phone.startswith('+') and not phone.startswith('254'):
                    phone = '254' + phone
                if not phone.startswith('+'):
                    phone = '+' + phone
                    
                sms.send(message, [phone])
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send churn SMS to {customer.name}: {str(e)}")
                
    return sent_count
