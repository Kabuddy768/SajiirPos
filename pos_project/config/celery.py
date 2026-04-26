import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_project.config.settings')

app = Celery('pos_project')

app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
