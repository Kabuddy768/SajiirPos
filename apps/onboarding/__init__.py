"""
Onboarding App — Self-Signup & Workspace Provisioning
=======================================================

This Django app handles:
  - Public landing page
  - New tenant registration (Step 1: Account creation)
  - Workspace setup (Step 2: Subdomain + Plan selection)
  - Async tenant schema provisioning via Celery
"""
default_app_config = 'apps.onboarding.apps.OnboardingConfig'
