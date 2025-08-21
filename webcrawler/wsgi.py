"""
WSGI config for webcrawler project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webcrawler.settings')

# New Relic integration for WSGI
try:
    import newrelic.agent
    newrelic.agent.initialize('newrelic.ini')
    application = newrelic.agent.WSGIApplicationWrapper(get_wsgi_application())
except ImportError:
    application = get_wsgi_application()
