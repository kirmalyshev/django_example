"""
ASGI entrypoint. Configures Django and then runs the application
defined in the ASGI_APPLICATION setting.
"""

import os

import django

django.setup()
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_example.settings")
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from django.conf import settings
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

import apps.integration.routing

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        'websocket': AuthMiddlewareStack(URLRouter(apps.integration.routing.websocket_urlpatterns)),
    }
)

if settings.SENTRY_PROJECT_ID and settings.SENTRY_TOKEN:
    sentry_asgi_app = SentryAsgiMiddleware(application)
