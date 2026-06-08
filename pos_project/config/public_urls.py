"""
Public Schema URL Configuration
=================================
These routes are served from the root domain (www.sajiirpos.com / localhost).
They handle the landing page, registration, onboarding wizard, and public APIs.

This file is referenced by PUBLIC_SCHEMA_URLCONF in settings.
"""
from django.urls import path, include
from django.contrib import admin
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.onboarding.views import (
    landing_page,
    tenant_register,
    tenant_workspace_setup,
    tenant_creation_pending,
    tenant_creation_status,
)

urlpatterns = [
    # ── Admin ─────────────────────────────────────────────────────
    path('admin/', admin.site.urls),

    # ── API Auth (also available on public schema) ─────────────────
    path('api/v1/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # ── Public Landing ─────────────────────────────────────────────
    path('', landing_page, name='landing_page'),

    # ── Self-Signup Onboarding Wizard ──────────────────────────────
    path('register/', tenant_register, name='tenant_register'),
    path('register/workspace/', tenant_workspace_setup, name='tenant_workspace_setup'),
    path('register/pending/', tenant_creation_pending, name='tenant_creation_pending'),
    path('register/status/', tenant_creation_status, name='tenant_creation_status'),
]
