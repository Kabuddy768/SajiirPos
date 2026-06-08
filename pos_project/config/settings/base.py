import os
from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

SECRET_KEY = config('SECRET_KEY', default='unsafe-secret-key')
DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1,.localhost').split(',')

SHARED_APPS = [
    'django_tenants',
    'apps.tenants',
    'apps.accounts',
    'apps.onboarding',  # Public signup — lives in the shared schema

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'rest_framework_simplejwt',
    'channels',
    'corsheaders',
]

# Use Argon2 for stronger password hashing (memory-hard, resistant to brute-force)
# Install: pip install django[argon2]
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',  # fallback for existing passwords
]

TENANT_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',

    'apps.branches',
    'apps.products',
    'apps.inventory',
    'apps.sales',
    'apps.payments',
    'apps.purchasing',
    'apps.returns',
    'apps.compliance',
    'apps.reports',
    'apps.customers',
    'apps.expenses',
    'apps.audit',
    'apps.invitations',
]

INSTALLED_APPS = list(SHARED_APPS) + [app for app in TENANT_APPS if app not in SHARED_APPS]

TENANT_MODEL = 'tenants.Tenant'
TENANT_DOMAIN_MODEL = 'tenants.Domain'
DATABASE_ROUTERS = ('django_tenants.routers.TenantSyncRouter', )

MIDDLEWARE = [
    'django_tenants.middleware.main.TenantMainMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.branches.middleware.BranchMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'pos_project.config.urls'
PUBLIC_SCHEMA_URLCONF = 'pos_project.config.public_urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'frontend', 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'pos_project.config.wsgi.application'
ASGI_APPLICATION = 'pos_project.config.asgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django_tenants.postgresql_backend',
        'NAME': 'pos_db',
        'USER': 'postgres',
        'PASSWORD': 'password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
import dj_database_url
db_from_env = dj_database_url.config(default=config('DATABASE_URL', default='postgres://postgres:postgres@localhost:5432/pos_db'))
db_from_env['ENGINE'] = 'django_tenants.postgresql_backend'
DATABASES['default'].update(db_from_env)

AUTH_USER_MODEL = 'accounts.CustomUser'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/day',
        'user': '1000/day'
    }
}

CORS_ALLOW_ALL_ORIGINS = config('CORS_ALLOW_ALL_ORIGINS', default=False, cast=bool)
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='http://localhost:3000').split(',')

from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
}

REDIS_URL = config('REDIS_URL', default='redis://localhost:6379/0')

# Gracefully fall back to local memory cache if Redis is not running
import redis
try:
    _redis_client = redis.Redis.from_url(REDIS_URL, socket_connect_timeout=1)
    _redis_client.ping()
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
            }
        }
    }
    CELERY_TASK_ALWAYS_EAGER = False
except Exception:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "sajiir-pos-fallback",
        }
    }
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [REDIS_URL],
        },
    },
}

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Africa/Nairobi'

# Fail fast if Redis/Celery is offline (do not block the web process retrying to connect)
CELERY_BROKER_CONNECTION_MAX_RETRIES = 1
CELERY_BROKER_TRANSPORT_OPTIONS = {
    'max_retries': 1,
    'interval_start': 0.1,
    'interval_step': 0.1,
    'interval_max': 0.2,
}


from celery.schedules import crontab
CELERY_BEAT_SCHEDULE = {
    'check-expiry-daily': {
        'task': 'workers.expiry_check.check_expiry_dates',
        'schedule': crontab(hour=7, minute=0),
    },
    'check-inventory-levels-hourly': {
        'task': 'workers.inventory_alerts.check_inventory_levels',
        'schedule': crontab(minute=0),
    },
    # NOTE: detect_churned_customers and generate_demand_based_po now require
    # a schema_name argument. They cannot be called directly from Beat without
    # per-tenant dispatch. Use a management command that iterates Client.objects.all()
    # and calls .delay(schema_name=client.schema_name) for each tenant.
    # 'detect-churned-customers-daily': {
    #     'task': 'workers.loyalty_tasks.detect_churned_customers',
    #     'schedule': crontab(hour=8, minute=0),
    # },
    'cleanup-sale-counters-weekly': {
        'task': 'workers.maintenance_tasks.cleanup_daily_sale_counters',
        'schedule': crontab(hour=3, minute=0, day_of_week=0),  # Every Sunday 3am
    },
    'dispatch-daily-tenant-tasks': {
        'task': 'workers.maintenance_tasks.dispatch_daily_tenant_tasks',
        'schedule': crontab(hour=6, minute=30),  # 6:30 AM daily
    },
    'dispatch-hourly-etims-retry': {
        'task': 'workers.maintenance_tasks.dispatch_hourly_etims_retry',
        'schedule': crontab(minute=0),  # Every hour
    },
}



LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Nairobi'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'frontend', 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '[{levelname}] {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'sajiir.log'),
            'maxBytes': 1024 * 1024 * 5,  # 5MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'error_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'errors.log'),
            'maxBytes': 1024 * 1024 * 5,
            'backupCount': 5,
            'level': 'ERROR',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'apps': {  # catches all your app logs
            'handlers': ['console', 'file', 'error_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'workers': {  # catches all celery task logs
            'handlers': ['console', 'file', 'error_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'pos_checkout'
LOGOUT_REDIRECT_URL = 'login'

AFRICASTALKING_USERNAME = config('AFRICASTALKING_USERNAME', default='sandbox')
AFRICASTALKING_API_KEY = config('AFRICASTALKING_API_KEY', default='')

# ── Email ────────────────────────────────────────────────────────────
# In development use console backend; in production set EMAIL_BACKEND to SMTP.
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@sajiir.co.ke')

# ── Security Hardening ────────────────────────────────────────────────
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_HTTPONLY = True

# Only enable these if using HTTPS
if not DEBUG:
    SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# M-Pesa webhook security
MPESA_CALLBACK_SECRET = config('MPESA_CALLBACK_SECRET', default='')

# M-Pesa Daraja API Settings
MPESA_CONSUMER_KEY = config('MPESA_CONSUMER_KEY', default='')
MPESA_CONSUMER_SECRET = config('MPESA_CONSUMER_SECRET', default='')
MPESA_PASSKEY = config('MPESA_PASSKEY', default='')
MPESA_SHORTCODE = config('MPESA_SHORTCODE', default='')
MPESA_CALLBACK_URL = config('MPESA_CALLBACK_URL', default='')
MPESA_ENV = config('MPESA_ENV', default='sandbox')


