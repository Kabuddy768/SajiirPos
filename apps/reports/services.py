from decimal import Decimal
from django.db.models import Sum, Count, F, Q
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone
from datetime import timedelta

from apps.sales.models import Sale, SaleItem
from apps.inventory.models import BranchStock, StockMovement
from apps.expenses.models import Expense
from apps.returns.models import Return


class ReportService:
    """
    Centralised reporting queries.
    Every method returns plain dicts/lists — no model instances — so views
    can serialise them straight to JSON.
    """

    # ------------------------------------------------------------------
    # SALES REPORTS
    # ------------------------------------------------------------------
    @staticmethod
    def daily_sales_summary(branch, date=None):
        """Sales totals for a single day."""
        if date is None:
            date = timezone.localtime().date()

        sales = Sale.objects.filter(
            branch=branch,
            created_at__date=date,
            status='completed',
        )

        agg = sales.aggregate(
            total_sales=Sum('total_amount'),
            total_tax=Sum('tax_amount'),
            total_discount=Sum('discount_amount'),
            count=Count('id'),
        )

        return {
            'date': str(date),
            'branch': branch.name,
            'total_sales': float(agg['total_sales'] or 0),
            'total_tax': float(agg['total_tax'] or 0),
            'total_discount': float(agg['total_discount'] or 0),
            'transaction_count': agg['count'],
        }

    @staticmethod
    def sales_by_date_range(branch, start_date, end_date):
        """Daily breakdown over a date range."""
        rows = (
            Sale.objects
            .filter(
                branch=branch,
                created_at__date__gte=start_date,
                created_at__date__lte=end_date,
                status='completed',
            )
            .annotate(day=TruncDate('created_at'))
            .values('day')
            .annotate(
                total=Sum('total_amount'),
                tax=Sum('tax_amount'),
                count=Count('id'),
            )
            .order_by('day')
        )
        return [
            {
                'date': str(r['day']),
                'total_sales': float(r['total'] or 0),
                'total_tax': float(r['tax'] or 0),
                'transaction_count': r['count'],
            }
            for r in rows
        ]

    @staticmethod
    def top_products(branch, start_date, end_date, limit=20):
        """Best-selling products by revenue."""
        rows = (
            SaleItem.objects
            .filter(
                sale__branch=branch,
                sale__created_at__date__gte=start_date,
                sale__created_at__date__lte=end_date,
                sale__status='completed',
            )
            .values(product_name=F('product__name'))
            .annotate(
                qty_sold=Sum('quantity'),
                revenue=Sum('line_total'),
            )
            .order_by('-revenue')[:limit]
        )
        return [
            {
                'product': r['product_name'],
                'quantity_sold': float(r['qty_sold'] or 0),
                'revenue': float(r['revenue'] or 0),
            }
            for r in rows
        ]

    # ------------------------------------------------------------------
    # INVENTORY REPORTS
    # ------------------------------------------------------------------
    @staticmethod
    def stock_levels(branch):
        """Current stock levels at a branch."""
        rows = (
            BranchStock.objects
            .filter(branch=branch)
            .select_related('product')
            .order_by('product__name')
        )
        return [
            {
                'product': bs.product.name,
                'sku': bs.product.sku,
                'quantity': float(bs.quantity),
                'cost_price': float(bs.product.cost_price),
                'stock_value': float(bs.quantity * bs.product.cost_price),
            }
            for bs in rows
        ]

    @staticmethod
    def low_stock(branch, threshold=10):
        """Products below the given threshold."""
        rows = (
            BranchStock.objects
            .filter(branch=branch, quantity__lt=threshold)
            .select_related('product')
            .order_by('quantity')
        )
        return [
            {
                'product': bs.product.name,
                'sku': bs.product.sku,
                'quantity': float(bs.quantity),
            }
            for bs in rows
        ]

    @staticmethod
    def stock_movement_history(branch, start_date, end_date):
        """Stock movements over a period."""
        rows = (
            StockMovement.objects
            .filter(
                branch=branch,
                created_at__date__gte=start_date,
                created_at__date__lte=end_date,
            )
            .select_related('product', 'performed_by')
            .order_by('-created_at')[:500]
        )
        return [
            {
                'date': str(m.created_at),
                'product': m.product.name,
                'reason': m.reason,
                'quantity': float(m.quantity),
                'before': float(m.quantity_before),
                'after': float(m.quantity_after),
                'performed_by': m.performed_by.email,
                'reference': m.reference_id,
            }
            for m in rows
        ]

    # ------------------------------------------------------------------
    # FINANCIAL REPORTS
    # ------------------------------------------------------------------
    @staticmethod
    def profit_loss(branch, start_date, end_date):
        """Simple P&L: Revenue - COGS - Expenses."""
        # Revenue
        revenue_agg = (
            Sale.objects
            .filter(
                branch=branch,
                created_at__date__gte=start_date,
                created_at__date__lte=end_date,
                status='completed',
            )
            .aggregate(revenue=Sum('total_amount'), tax=Sum('tax_amount'))
        )
        revenue = Decimal(str(revenue_agg['revenue'] or 0))
        tax_collected = Decimal(str(revenue_agg['tax'] or 0))

        # COGS (cost of goods sold)
        cogs_agg = (
            SaleItem.objects
            .filter(
                sale__branch=branch,
                sale__created_at__date__gte=start_date,
                sale__created_at__date__lte=end_date,
                sale__status='completed',
            )
            .aggregate(cogs=Sum(F('cost_price') * F('quantity')))
        )
        cogs = Decimal(str(cogs_agg['cogs'] or 0))

        # Expenses
        expense_agg = (
            Expense.objects
            .filter(
                branch=branch,
                paid_on__gte=start_date,
                paid_on__lte=end_date,
            )
            .aggregate(total=Sum('amount'))
        )
        expenses = Decimal(str(expense_agg['total'] or 0))

        # Refunds
        refund_agg = (
            Return.objects
            .filter(
                branch=branch,
                created_at__date__gte=start_date,
                created_at__date__lte=end_date,
            )
            .aggregate(total=Sum('refund_amount'))
        )
        refunds = Decimal(str(refund_agg['total'] or 0))

        gross_profit = revenue - cogs - refunds
        net_profit = gross_profit - expenses

        return {
            'period': f"{start_date} to {end_date}",
            'branch': branch.name,
            'revenue': float(revenue),
            'tax_collected': float(tax_collected),
            'cost_of_goods_sold': float(cogs),
            'refunds': float(refunds),
            'gross_profit': float(gross_profit),
            'expenses': float(expenses),
            'net_profit': float(net_profit),
        }

    @staticmethod
    def expense_breakdown(branch, start_date, end_date):
        """Expenses grouped by category."""
        rows = (
            Expense.objects
            .filter(
                branch=branch,
                paid_on__gte=start_date,
                paid_on__lte=end_date,
            )
            .values(category_name=F('category__name'))
            .annotate(total=Sum('amount'), count=Count('id'))
            .order_by('-total')
        )
        return [
            {
                'category': r['category_name'] or 'Uncategorized',
                'total': float(r['total'] or 0),
                'count': r['count'],
            }
            for r in rows
        ]
