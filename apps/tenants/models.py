from django.db import models
from django_tenants.models import TenantMixin, DomainMixin
from django.conf import settings

class Tenant(TenantMixin):
    name = models.CharField(max_length=100)
    uuid = models.UUIDField(unique=True, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    plan = models.CharField(max_length=50, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=2, default='KE')
    currency = models.CharField(max_length=3, default='KES')
    kra_pin = models.CharField(max_length=20, blank=True)
    etims_serial = models.CharField(max_length=50, blank=True)
    etims_activated = models.BooleanField(default=False)
    vat_registered = models.BooleanField(default=False)
    vat_registration_no = models.CharField(max_length=50, blank=True)
    
    users = models.ManyToManyField(settings.AUTH_USER_MODEL, through='TenantUser')

    auto_create_schema = True

    def __str__(self):
        return self.name

class Domain(DomainMixin):
    pass

class TenantUser(models.fields.related.RelatedField if False else models.Model):
    ROLE_OWNER = 'owner'
    ROLE_ADMIN = 'admin'
    ROLE_MANAGER = 'manager'
    ROLE_CASHIER = 'cashier'
    ROLE_AUDITOR = 'auditor'

    ROLE_CHOICES = [
        (ROLE_OWNER, 'Owner'),
        (ROLE_ADMIN, 'Admin'),
        (ROLE_MANAGER, 'Manager'),
        (ROLE_CASHIER, 'Cashier'),
        (ROLE_AUDITOR, 'Auditor'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    is_active = models.BooleanField(default=True)
    branch = models.ForeignKey('branches.Branch', on_delete=models.SET_NULL, null=True, blank=True)
    join_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'tenant')

    def __str__(self):
        return f"{self.user.email} - {self.role} at {self.tenant.name}"
