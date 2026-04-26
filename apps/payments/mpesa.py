import logging

logger = logging.getLogger(__name__)

class MpesaClient:
    def __init__(self, tenant=None):
        self.tenant = tenant

    def initiate_stk_push(self, phone_number, amount, reference, description="Payment"):
        logger.info(f"Initiating STK push to {phone_number} for {amount}")
        return {
            "ResponseCode": "0",
            "CheckoutRequestID": "ws_CO_1234567890",
            "CustomerMessage": "Success. Request accepted for processing"
        }
