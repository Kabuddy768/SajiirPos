from django.db import models

class LoyaltyTier(models.Model):
    name = models.CharField(max_length=50)
    min_points = models.IntegerField(default=0)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    
    def __str__(self):
        return self.name

class Customer(models.Model):
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, unique=True, null=True, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    loyalty_points = models.IntegerField(default=0)
    tier = models.ForeignKey(LoyaltyTier, on_delete=models.SET_NULL, null=True, blank=True)
    last_purchase_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # ── Credit Control ───────────────────────────────────────
    allow_credit_sales = models.BooleanField(default=False)
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    current_credit_balance = models.DecimalField(
        max_digits=12, decimal_places=2, default=0.00,
        help_text='Running outstanding balance. Positive = owes money.'
    )

    def __str__(self):
        return f"{self.name} ({self.phone})"


class CustomerCreditLedger(models.Model):
    """Append-only ledger for all credit charges and repayments."""
    TYPE_CHARGE  = 'charge'
    TYPE_PAYMENT = 'payment'
    TRANSACTION_TYPES = [
        (TYPE_CHARGE,  'Credit Purchase'),
        (TYPE_PAYMENT, 'Credit Repayment'),
    ]

    customer         = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='ledger_entries')
    sale             = models.ForeignKey('sales.Sale', on_delete=models.SET_NULL, null=True, blank=True)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    amount           = models.DecimalField(max_digits=12, decimal_places=2)
    reference        = models.CharField(max_length=100, blank=True,
                                        help_text='M-Pesa receipt, bank ref, or cash receipt no.')
    notes            = models.TextField(blank=True)
    recorded_by      = models.ForeignKey(
        'accounts.CustomUser', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='credit_ledger_entries'
    )
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_transaction_type_display()} — {self.amount} ({self.customer.name})"
