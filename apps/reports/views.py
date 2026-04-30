from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.utils import timezone
from datetime import datetime

from apps.tenants.permissions import IsCashier
from apps.branches.models import Branch
from .services import ReportService


class _BaseReportView(APIView):
    """Shared logic: resolve branch and date range from query params."""
    permission_classes = [IsAuthenticated, IsCashier]

    def _resolve_params(self, request):
        branch_id = request.query_params.get('branch_id')
        if not branch_id:
            return None, None, None, Response(
                {'error': 'branch_id is required.'}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            branch = Branch.objects.get(id=branch_id)
        except Branch.DoesNotExist:
            return None, None, None, Response(
                {'error': 'Branch not found.'}, status=status.HTTP_404_NOT_FOUND
            )

        start = request.query_params.get('start_date')
        end = request.query_params.get('end_date')

        today = timezone.localtime().date()
        start_date = datetime.strptime(start, '%Y-%m-%d').date() if start else today
        end_date = datetime.strptime(end, '%Y-%m-%d').date() if end else today

        return branch, start_date, end_date, None


# ------------------------------------------------------------------
# Sales
# ------------------------------------------------------------------

class DailySalesSummaryView(_BaseReportView):
    def get(self, request):
        branch, start_date, _, err = self._resolve_params(request)
        if err:
            return err
        data = ReportService.daily_sales_summary(branch, date=start_date)
        return Response(data)


class SalesDateRangeView(_BaseReportView):
    def get(self, request):
        branch, start_date, end_date, err = self._resolve_params(request)
        if err:
            return err
        data = ReportService.sales_by_date_range(branch, start_date, end_date)
        return Response(data)


class TopProductsView(_BaseReportView):
    def get(self, request):
        branch, start_date, end_date, err = self._resolve_params(request)
        if err:
            return err
        limit = int(request.query_params.get('limit', 20))
        data = ReportService.top_products(branch, start_date, end_date, limit)
        return Response(data)


# ------------------------------------------------------------------
# Inventory
# ------------------------------------------------------------------

class StockLevelsView(_BaseReportView):
    def get(self, request):
        branch, _, _, err = self._resolve_params(request)
        if err:
            return err
        data = ReportService.stock_levels(branch)
        return Response(data)


class LowStockView(_BaseReportView):
    def get(self, request):
        branch, _, _, err = self._resolve_params(request)
        if err:
            return err
        threshold = int(request.query_params.get('threshold', 10))
        data = ReportService.low_stock(branch, threshold)
        return Response(data)


class StockMovementHistoryView(_BaseReportView):
    def get(self, request):
        branch, start_date, end_date, err = self._resolve_params(request)
        if err:
            return err
        data = ReportService.stock_movement_history(branch, start_date, end_date)
        return Response(data)


# ------------------------------------------------------------------
# Financial
# ------------------------------------------------------------------

class ProfitLossView(_BaseReportView):
    def get(self, request):
        branch, start_date, end_date, err = self._resolve_params(request)
        if err:
            return err
        data = ReportService.profit_loss(branch, start_date, end_date)
        return Response(data)


class ExpenseBreakdownView(_BaseReportView):
    def get(self, request):
        branch, start_date, end_date, err = self._resolve_params(request)
        if err:
            return err
        data = ReportService.expense_breakdown(branch, start_date, end_date)
        return Response(data)
