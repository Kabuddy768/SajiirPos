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
        Aggregates directly from Sale model to avoid join distortion bugs.
        """
        from django.db.models.functions import Coalesce
        from decimal import Decimal
        
        start_date = timezone.now() - datetime.timedelta(days=days)
        
        # Filter for sales in the given period
        sales_filter = Q(created_at__gte=start_date)
        if branch:
            sales_filter &= Q(branch=branch)
            
        # Group by cashier and calculate stats directly from Sale model.
        # This is 100% safe from join-induced duplication distortion.
        cashier_stats = Sale.objects.filter(sales_filter).values(
            'cashier_id', 
            'cashier__first_name', 
            'cashier__last_name', 
            'cashier__email'
        ).annotate(
            total_sales_count=Count('id'),
            voided_sales_count=Count('id', filter=Q(status='voided')),
            total_revenue=Coalesce(Sum('total_amount', filter=Q(status='completed')), Decimal('0')),
            total_discounts=Coalesce(Sum('discount_amount', filter=Q(status='completed')), Decimal('0'))
        )

        metrics = []
        for stat in cashier_stats:
            total_sales = stat['total_sales_count']
            voided_sales = stat['voided_sales_count']
            revenue = float(stat['total_revenue'])
            discounts = float(stat['total_discounts'])
            
            void_rate = (voided_sales / total_sales * 100) if total_sales > 0 else 0
            potential_revenue = revenue + discounts
            discount_rate = (discounts / potential_revenue * 100) if potential_revenue > 0 else 0
            
            name = f"{stat['cashier__first_name']} {stat['cashier__last_name']}".strip()
            if not name:
                name = stat['cashier__email']

            metrics.append({
                'cashier_id': stat['cashier_id'],
                'cashier_name': name,
                'total_sales': total_sales,
                'voided_sales': voided_sales,
                'void_rate': round(void_rate, 2),
                'discount_rate': round(discount_rate, 2),
                'total_revenue': revenue
            })

        # Sort by void rate descending to highlight potential issues
        metrics.sort(key=lambda x: x['void_rate'], reverse=True)
        return metrics

