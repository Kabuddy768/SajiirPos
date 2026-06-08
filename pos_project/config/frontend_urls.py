from django.urls import path
from django.contrib.auth import views as auth_views
from apps.sales.views_frontend import (
    session_open, checkout, session_close, z_report, product_lookup,
    sale_list, sale_detail
)
from apps.reports.views_frontend import (
    dashboard, etims_dashboard, dashboard_staff, profit_loss_report,
    etims_retry_all, etims_pending_invoices,
    credit_aging_report, record_credit_payment,
    payables_report, record_supplier_payment,
    staff_performance_report,
)


from apps.accounts.views import login_step1, login_step2
from apps.invitations.views import invite_send, invite_accept
from apps.products.views_frontend import (
    product_list, product_create, product_update, product_delete, product_import,
    product_barcode
)
from apps.branches.views_frontend import (
    branch_list, branch_create, branch_update
)
from apps.inventory.views_frontend import (
    stock_list, stock_movements, transfer_list, transfer_detail
)
from apps.purchasing.views_frontend import (
    supplier_list, supplier_create, supplier_update, supplier_delete,
    grn_list, grn_create
)
from apps.tenants.views import subscription_page, workspace_settings
from apps.returns.views_frontend import process_return

from apps.expenses.views_frontend import (
    expense_list, expense_create, expense_delete
)

from apps.customers.views_frontend import (
    customer_list, customer_create, customer_update, customer_detail
)

urlpatterns = [
    # ── Auth: two-step login ──────────────────────────────────────
    path("login/", login_step1, name="login"),
    path("login/password/", login_step2, name="login_password"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    # ── POS till ─────────────────────────────────────────────────
    path("", checkout, name="pos_checkout"),
    path("session/open/", session_open, name="session_open"),
    path("session/close/", session_close, name="session_close"),
    path("session/z-report/<int:session_id>/", z_report, name="z_report"),
    path("api/product-lookup/", product_lookup, name="product_lookup"),

    # ── Dashboard ─────────────────────────────────────────────────
    path("dashboard/", dashboard, name="dashboard"),
    path("dashboard/reports/pl/", profit_loss_report, name="profit_loss_report"),
    path("dashboard/etims/", etims_dashboard, name="etims_dashboard"),
    path("dashboard/etims/retry-all/", etims_retry_all, name="etims_retry_all"),
    path("dashboard/etims/pending/", etims_pending_invoices, name="etims_pending_invoices"),


    path("dashboard/staff/", dashboard_staff, name="dashboard_staff"),

    # ── Products CRUD ──────────────────────────────────────────────
    path("dashboard/products/", product_list, name="product_list"),
    path("dashboard/products/add/", product_create, name="product_create"),
    path("dashboard/products/import/", product_import, name="product_import"),
    path("dashboard/products/<int:pk>/edit/", product_update, name="product_update"),
    path("dashboard/products/<int:pk>/delete/", product_delete, name="product_delete"),
    path("dashboard/products/<int:pk>/barcode/", product_barcode, name="product_barcode"),

    # ── Branches CRUD ──────────────────────────────────────────────
    path("dashboard/branches/", branch_list, name="branch_list"),
    path("dashboard/branches/add/", branch_create, name="branch_create"),
    path("dashboard/branches/<int:pk>/edit/", branch_update, name="branch_update"),

    # ── Inventory & Stock ──────────────────────────────────────────
    path("dashboard/inventory/", stock_list, name="stock_list"),
    path("dashboard/inventory/movements/", stock_movements, name="stock_movements"),
    path("dashboard/inventory/transfers/", transfer_list, name="transfer_list"),
    path("dashboard/inventory/transfers/<int:pk>/", transfer_detail, name="transfer_detail"),

    # ── Sales History & Returns ────────────────────────────────────
    path("dashboard/sales/", sale_list, name="sale_list"),
    path("dashboard/sales/<int:pk>/", sale_detail, name="sale_detail"),
    path("dashboard/sales/<int:sale_id>/return/", process_return, name="process_return"),

    # ── Customers & Loyalty ────────────────────────────────────────
    path("dashboard/customers/", customer_list, name="customer_list"),
    path("dashboard/customers/add/", customer_create, name="customer_create"),
    path("dashboard/customers/<int:pk>/edit/", customer_update, name="customer_update"),
    path("dashboard/customers/<int:pk>/", customer_detail, name="customer_detail"),

    # ── Expenses ───────────────────────────────────────────────────
    path("dashboard/expenses/", expense_list, name="expense_list"),
    path("dashboard/expenses/add/", expense_create, name="expense_create"),
    path("dashboard/expenses/<int:pk>/delete/", expense_delete, name="expense_delete"),

    # ── Subscription ──────────────────────────────────────────────
    path("dashboard/subscription/", subscription_page, name="subscription_page"),
    path("dashboard/settings/", workspace_settings, name="workspace_settings"),

    # ── Staff invitations ─────────────────────────────────────────
    path("dashboard/invite/send/", invite_send, name="invite_send"),
    path("invite/accept/", invite_accept, name="invite_accept"),

    # ── Financial Reports ─────────────────────────────────────────
    path("dashboard/reports/credit-aging/",       credit_aging_report,      name="credit_aging_report"),
    path("dashboard/reports/payables/",            payables_report,          name="payables_report"),
    path("dashboard/reports/staff-performance/",   staff_performance_report, name="staff_performance_report"),
    path("dashboard/customers/<int:customer_id>/record-payment/", record_credit_payment,  name="record_credit_payment"),
    path("dashboard/suppliers/<int:supplier_id>/record-payment/", record_supplier_payment, name="record_supplier_payment"),

    # ── Suppliers & GRNs ──────────────────────────────────────────
    path("dashboard/suppliers/", supplier_list, name="supplier_list"),
    path("dashboard/suppliers/add/", supplier_create, name="supplier_create"),
    path("dashboard/suppliers/<int:pk>/edit/", supplier_update, name="supplier_update"),
    path("dashboard/suppliers/<int:pk>/delete/", supplier_delete, name="supplier_delete"),
    path("dashboard/grns/", grn_list, name="grn_list"),
    path("dashboard/grns/add/", grn_create, name="grn_create"),
]
