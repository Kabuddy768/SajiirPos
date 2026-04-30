from django.contrib import admin
from .models import ExpenseCategory, Expense


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['description', 'amount', 'category', 'branch', 'paid_on', 'recorded_by', 'created_at']
    list_filter = ['category', 'branch', 'paid_on']
    search_fields = ['description']
    readonly_fields = ['created_at']
