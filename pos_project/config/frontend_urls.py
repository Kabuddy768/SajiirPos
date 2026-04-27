from django.urls import path
from django.contrib.auth import views as auth_views
from apps.sales.views_frontend import (
    session_open, checkout, session_close, z_report, product_lookup
)

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(template_name="accounts/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    
    path("", checkout, name="pos_checkout"),
    path("session/open/", session_open, name="session_open"),
    path("session/close/", session_close, name="session_close"),
    path("session/z-report/<int:session_id>/", z_report, name="z_report"),
    path("api/product-lookup/", product_lookup, name="product_lookup"),
]
