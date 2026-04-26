from django.contrib import admin
from .models import Branch

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ['name', 'etims_branch_code', 'address', 'phone', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'etims_branch_code']
    readonly_fields = ['created_at']
