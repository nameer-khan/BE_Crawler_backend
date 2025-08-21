"""
Celery configuration for webcrawler project.
"""

import os
from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webcrawler.settings')

# New Relic integration for Celery
try:
    import newrelic.agent
    newrelic.agent.initialize('newrelic.ini')
except ImportError:
    pass

app = Celery('webcrawler')

# Load task modules from all registered Django apps
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()

# Explicitly set broker URL
app.conf.broker_url = settings.CELERY_BROKER_URL
app.conf.result_backend = settings.CELERY_RESULT_BACKEND

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
