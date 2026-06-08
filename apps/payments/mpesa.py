import logging
import base64
from datetime import datetime
import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

class MpesaClient:
    def __init__(self, tenant=None, branch=None):
        self.tenant = tenant
        self.branch = branch
        self.callback_url = getattr(settings, 'MPESA_CALLBACK_URL', '')

        # Load from branch settings if configured, otherwise fall back to global settings
        if branch and branch.mpesa_shortcode:
            self.consumer_key = branch.mpesa_consumer_key
            self.consumer_secret = branch.mpesa_consumer_secret
            self.passkey = branch.mpesa_passkey
            self.shortcode = branch.mpesa_shortcode
            self.env = branch.mpesa_env
        else:
            self.consumer_key = getattr(settings, 'MPESA_CONSUMER_KEY', '')
            self.consumer_secret = getattr(settings, 'MPESA_CONSUMER_SECRET', '')
            self.passkey = getattr(settings, 'MPESA_PASSKEY', '')
            self.shortcode = getattr(settings, 'MPESA_SHORTCODE', '')
            self.env = getattr(settings, 'MPESA_ENV', 'sandbox')

        if self.env == 'production':
            self.base_url = 'https://api.safaricom.co.ke'
        else:
            self.base_url = 'https://sandbox.safaricom.co.ke'

    def get_access_token(self):
        """
        Generates OAuth access token from Safaricom Daraja API.
        Caches the token for 50 minutes (Safaricom tokens expire after 60min).
        """
        from django.core.cache import cache
        
        if self.branch:
            cache_key = f"mpesa_token_branch_{self.branch.id}_{self.env}"
        else:
            cache_key = f"mpesa_token_{self.env}"

        cached_token = cache.get(cache_key)
        if cached_token:
            return cached_token

        url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
        if not self.consumer_key or not self.consumer_secret:
            logger.error("M-Pesa Consumer Key or Consumer Secret is missing.")
            return None
            
        try:
            response = requests.get(
                url, 
                auth=(self.consumer_key, self.consumer_secret),
                timeout=10
            )
            response.raise_for_status()
            token_data = response.json()
            token = token_data.get('access_token')
            if token:
                cache.set(cache_key, token, 50 * 60)  # cache for 50 minutes
            return token
        except Exception as e:
            logger.error(f"Failed to get M-Pesa access token: {str(e)}")
            return None

    def initiate_stk_push(self, phone_number, amount, reference, description="Payment"):
        """
        Initiates a Lipa Na M-Pesa Online (STK Push) transaction.
        """
        token = self.get_access_token()
        if not token:
            return {
                "ResponseCode": "99",
                "CustomerMessage": "Failed to authenticate with M-Pesa. Please check credentials."
            }

        # Format phone number to 2547XXXXXXXX or 2541XXXXXXXX
        phone_number = str(phone_number).strip().replace('+', '')
        if phone_number.startswith('0'):
            phone_number = '254' + phone_number[1:]
        elif phone_number.startswith('7') or phone_number.startswith('1'):
            phone_number = '254' + phone_number

        # Timestamp in YYYYMMDDHHmmss format (EAT time: UTC+3)
        # Using Django's configured timezone (Africa/Nairobi) to match local time
        timestamp = timezone.localtime(timezone.now()).strftime('%Y%m%d%H%M%S')

        # Password is base64(Shortcode + Passkey + Timestamp)
        password_str = f"{self.shortcode}{self.passkey}{timestamp}"
        password = base64.b64encode(password_str.encode('utf-8')).decode('utf-8')

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # Lipa Na Mpesa Online payload
        # Cast Shortcodes and Phone numbers to integers to match "Type: Numeric" requirements.
        # Enforce max 12 chars for AccountReference and max 13 chars for TransactionDesc.
        safe_reference = str(reference).replace('-', '')[:12]
        if not safe_reference:
            safe_reference = "POSPay"
            
        safe_description = str(description)[:13]
        if not safe_description:
            safe_description = "Payment"

        payload = {
            "BusinessShortCode": int(self.shortcode),
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",  # default sandbox type
            "Amount": int(float(amount)),
            "PartyA": int(phone_number),
            "PartyB": int(self.shortcode),
            "PhoneNumber": int(phone_number),
            "CallBackURL": self.callback_url,
            "AccountReference": safe_reference,
            "TransactionDesc": safe_description
        }


        url = f"{self.base_url}/mpesa/stkpush/v1/processrequest"
        try:
            logger.info(f"Initiating STK push request to Safaricom: {payload}")
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            response_data = response.json()
            logger.info(f"Safaricom STK push response: {response_data}")
            return response_data
        except Exception as e:
            logger.error(f"Error initiating M-Pesa STK push: {str(e)}")
            return {
                "ResponseCode": "99",
                "CustomerMessage": f"An error occurred while communicating with M-Pesa: {str(e)}"
            }

    def query_stk_status(self, checkout_request_id):
        """
        Queries Safaricom to check if a specific STK push transaction
        was completed, cancelled, or is still pending.
        Returns: dict with ResultCode (0 = success, 1032 = cancelled, etc.)
        """
        token = self.get_access_token()
        if not token:
            return {"ResultCode": "99", "ResultDesc": "Failed to get access token"}

        timestamp = timezone.localtime(timezone.now()).strftime('%Y%m%d%H%M%S')
        password_str = f"{self.shortcode}{self.passkey}{timestamp}"
        password = base64.b64encode(password_str.encode('utf-8')).decode('utf-8')

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        payload = {
            "BusinessShortCode": int(self.shortcode),
            "Password": password,
            "Timestamp": timestamp,
            "CheckoutRequestID": checkout_request_id,
        }

        url = f"{self.base_url}/mpesa/stkpushquery/v1/query"
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            data = response.json()
            logger.info(f"STK query response for {checkout_request_id}: {data}")
            return data
        except Exception as e:
            logger.error(f"STK query error: {str(e)}")
            return {"ResultCode": "99", "ResultDesc": str(e)}
