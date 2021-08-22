from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.conf import settings
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

import apps.integration.routing

application = ProtocolTypeRouter(
    {
        # (http->django views is added by default)
        'websocket': AuthMiddlewareStack(URLRouter(apps.integration.routing.websocket_urlpatterns)),
    }
)


if settings.SENTRY_PROJECT_ID and settings.SENTRY_TOKEN:
    sentry_asgi_app = SentryAsgiMiddleware(application)
