"""
KRA eTIMS Integration Client
=============================

STATUS: STUB — Real KRA API integration pending.

This module is a placeholder. It simulates eTIMS invoice signing so the rest
of the POS pipeline (sale → Celery task → sign) works end-to-end without
hitting the real KRA servers.

WHEN CREDENTIALS ARE AVAILABLE:
    1. Obtain ETIMS_CLIENT_ID, ETIMS_CLIENT_SECRET, and ETIMS_DEVICE_SERIAL
       from the KRA eTIMS developer portal (https://etims.kra.go.ke).
    2. Add them to the .env file (see .env.example for the variable names).
    3. Replace the stub logic in sign_sale() with actual HTTP calls to the
       KRA eTIMS API endpoints:
         - POST /api/v1/trnsSales/saveSales  (submit invoice)
         - The response will contain the signed QR code and invoice number.
    4. Populate sale.etims_qr_code and sale.etims_signature from the response.
    5. Set ETIMS_ENV to 'production' in .env when going live.

This stub will remain functional for development and testing until then.
"""

import logging

logger = logging.getLogger(__name__)


class ETIMSError(Exception):
    pass


class ETIMSClient:
    """
    TODO: Replace this stub with real KRA eTIMS API calls once credentials
    are obtained. The current implementation simulates a successful signing
    so the sale pipeline can be tested end-to-end.

    Required env vars (not yet available):
        - ETIMS_CLIENT_ID
        - ETIMS_CLIENT_SECRET
        - ETIMS_DEVICE_SERIAL
        - ETIMS_ENV  (sandbox / production)
    """

    def __init__(self, branch):
        self.branch = branch

    def sign_sale(self, sale):
        """
        Simulate eTIMS invoice signing.

        In production this method will:
        1. Build the invoice payload from sale + sale.items
        2. Authenticate with KRA using ETIMS_CLIENT_ID / SECRET
        3. POST the payload to the eTIMS saveSales endpoint
        4. Store the returned invoice number, QR code, and signature
        5. Mark etims_submission_status = 'submitted'

        For now it just stamps a fake invoice number so the flow completes.
        """
        try:
            # --- STUB: replace with real API call ---
            logger.info(
                f"[eTIMS STUB] Simulating signing for sale {sale.sale_number} "
                f"at branch {self.branch.name}"
            )
            sale.etims_invoice_number = f"ETIMS-STUB-{sale.id}"
            sale.etims_submission_status = 'submitted'
            sale.save(update_fields=['etims_invoice_number', 'etims_submission_status'])
            return True
        except Exception as e:
            logger.error(f"eTIMS signing failed: {str(e)}")
            raise ETIMSError(f"Failed to sign sale: {str(e)}")

