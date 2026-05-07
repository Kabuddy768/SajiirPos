import africastalking
from celery import shared_task
from django.conf import settings
from apps.sales.models import Sale
import logging

logger = logging.getLogger(__name__)

@shared_task
def send_whatsapp_receipt_task(sale_id, phone_number):
    """
    Send a simplified receipt via SMS/WhatsApp (Africa's Talking often uses SMS as fallback).
    """
    try:
        # Initialize Africa's Talking inside task to avoid module-level errors
        africastalking.initialize(
            settings.AFRICASTALKING_USERNAME,
            settings.AFRICASTALKING_API_KEY
        )
        sms = africastalking.SMS
    except Exception as e:
        logger.error(f"Failed to initialize Africa's Talking: {str(e)}")
        return str(e)


    try:
        sale = Sale.objects.get(id=sale_id)
        branch_name = sale.branch.name
        
        message = f"Receipt from {branch_name}\n"
        message += f"Sale #: {sale.sale_number}\n"
        message += f"Total: KES {sale.total_amount}\n"
        message += "Thank you for shopping with us!"
        
        # Ensure phone number is in international format for Africa's Talking
        clean_phone = str(phone_number).strip()
        if clean_phone.startswith('0'):
            clean_phone = '254' + clean_phone[1:]
        elif not clean_phone.startswith('+') and not clean_phone.startswith('254'):
            clean_phone = '254' + clean_phone
            
        if not clean_phone.startswith('+'):
            clean_phone = '+' + clean_phone
            
        response = sms.send(message, [clean_phone])
        logger.info(f"Receipt sent to {clean_phone}: {response}")
        return response
    except Exception as e:
        logger.error(f"Failed to send receipt for sale {sale_id}: {str(e)}")
        return str(e)
