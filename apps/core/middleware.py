from django.utils.deprecation import MiddlewareMixin

from apps.logging.handlers import RequestHandler
from apps.tools.http_client.handlers import HttpClientHandler


class HttpClientMiddleware(MiddlewareMixin):
    """
    Set `http_client` attribute on request, containing some info about remote http client
    """

    def process_request(self, request):
        request.http_client = HttpClientHandler(RequestHandler().get_user_agent(request))
