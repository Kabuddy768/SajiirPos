from django.urls import path
from .views import (
    DailySalesSummaryView,
    SalesDateRangeView,
    TopProductsView,
    StockLevelsView,
    LowStockView,
    StockMovementHistoryView,
    ProfitLossView,
    ExpenseBreakdownView,
    ETIMSCockpitView,
)

urlpatterns = [
    # Sales reports
    path('sales/daily/', DailySalesSummaryView.as_view(), name='report-daily-sales'),
    path('sales/range/', SalesDateRangeView.as_view(), name='report-sales-range'),
    path('sales/top-products/', TopProductsView.as_view(), name='report-top-products'),

    # Inventory reports
    path('inventory/stock-levels/', StockLevelsView.as_view(), name='report-stock-levels'),
    path('inventory/low-stock/', LowStockView.as_view(), name='report-low-stock'),
    path('inventory/movements/', StockMovementHistoryView.as_view(), name='report-stock-movements'),

    # Financial reports
    path('financial/profit-loss/', ProfitLossView.as_view(), name='report-profit-loss'),
    path('financial/expenses/', ExpenseBreakdownView.as_view(), name='report-expense-breakdown'),

    # eTIMS Cockpit
    path('etims/cockpit/', ETIMSCockpitView.as_view(), name='report-etims-cockpit'),
    path('etims/cockpit/export/', ETIMSCockpitView.as_view(), name='report-etims-cockpit-export'),
]
