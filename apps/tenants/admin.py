from django.contrib import admin
from .models import Tenant, Domain, TenantUser


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ['name', 'schema_name', 'contact_email', 'country', 'is_active', 'plan']
    list_filter = ['is_active', 'country', 'plan']
    search_fields = ['name', 'contact_email', 'schema_name']


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ['domain', 'tenant', 'is_primary']
    list_filter = ['is_primary']


@admin.register(TenantUser)
class TenantUserAdmin(admin.ModelAdmin):
    list_display = ['user', 'tenant', 'role', 'is_active', 'join_date']
    list_filter = ['role', 'is_active', 'tenant']
    search_fields = ['user__email', 'tenant__name']
