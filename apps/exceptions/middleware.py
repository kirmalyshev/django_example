from apps import logging

import psycopg2
from django.db import OperationalError
from django.http import HttpResponse
from django.template import RequestContext, loader
from psycopg2 import errorcodes

log = logging.getLogger(__name__)
ERROR_MESSAGES = [
    'не удалось получить блокировку',
    'could not obtain lock',
    'закрытие подключения',
    'remaining connection slots',
]


class OperationalErrorMiddleware:
    """
    Handle OperationalError:
        migration reset connect
        db lock row
        terminating connection due to administrator command
    """

    @classmethod
    def process_exception(cls, request, exc):
        if isinstance(exc, (OperationalError, psycopg2.OperationalError)):
            template = loader.get_template('500.html')
            status = None
            message = exc.message.decode('utf-8')
            pgcode = getattr(exc, 'pgcode', None)
            if pgcode:
                log.debug('Get pgcode of error: %s', pgcode)

            if any(msg in message for msg in ERROR_MESSAGES):
                status = 503
            elif (
                pgcode
                and pgcode == errorcodes.ADMIN_SHUTDOWN
                or 'SSL connection has been closed unexpectedly' in message
            ):
                status = 500

            if status:
                if status != 500:
                    log.error(message)
                context = {'extend_code': status}
                return HttpResponse(
                    template.render(RequestContext(request, context)),
                    status=status,
                    content_type='text/html; charset=utf-8',
                )
