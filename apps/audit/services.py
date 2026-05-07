from django.db.models import Count, Sum, Q
from django.utils import timezone
import datetime
from apps.sales.models import Sale
from django.contrib.auth import get_user_model

User = get_user_model()

class AuditService:
    @staticmethod
    def get_cashier_metrics(branch=None, days=30):
        """
        Calculate metrics for cashiers to detect anomalies like high void rates.
        """
        start_date = timezone.now() - datetime.timedelta(days=days)
        
        # Filter for sales in the given period
        sales_filter = Q(created_at__gte=start_date)
        if branch:
            sales_filter &= Q(branch=branch)
            
        # Group by cashier and calculate stats
        cashier_stats = User.objects.filter(
            sales__in=Sale.objects.filter(sales_filter)
        ).distinct().annotate(
            total_sales_count=Count('sales', filter=sales_filter),
            voided_sales_count=Count('sales', filter=sales_filter & Q(sales__status='voided')),
            total_revenue=Sum('sales__total_amount', filter=sales_filter & Q(sales__status='completed')),
            total_discounts=Sum('sales__discount_amount', filter=sales_filter & Q(sales__status='completed'))
        )
        
        metrics = []
        for cashier in cashier_stats:
            total_sales = cashier.total_sales_count
            voided_sales = cashier.voided_sales_count
            revenue = cashier.total_revenue or 0
            discounts = cashier.total_discounts or 0
            
            void_rate = (voided_sales / total_sales * 100) if total_sales > 0 else 0
            # Discount rate relative to potential revenue (revenue + discounts)
            potential_revenue = float(revenue) + float(discounts)
            discount_rate = (float(discounts) / potential_revenue * 100) if potential_revenue > 0 else 0
            
            metrics.append({
                'cashier_id': cashier.id,
                'cashier_name': cashier.get_full_name() or cashier.email,
                'total_sales': total_sales,
                'voided_sales': voided_sales,
                'void_rate': round(void_rate, 2),
                'discount_rate': round(discount_rate, 2),
                'total_revenue': float(revenue)
            })
            
        # Sort by void rate descending to highlight potential issues
        metrics.sort(key=lambda x: x['void_rate'], reverse=True)
        return metrics
