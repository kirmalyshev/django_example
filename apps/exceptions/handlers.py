# encoding=utf-8

import types

from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from django.utils.translation import ugettext as _
from rest_framework import exceptions as drf_exceptions
from rest_framework import status
from rest_framework.settings import api_settings
from rest_framework.views import Response, exception_handler as drf_exception_handler, set_rollback

from apps.exceptions import APIErrorList, APIError, decamelize


class RequestExceptionHandler:
    response_status = status.HTTP_400_BAD_REQUEST
    error_objects_key = 'api_errors'

    @classmethod
    def handle(cls, exception, context=None):
        exception_handler = cls(exception, context)
        handled = exception_handler.process_exception()
        set_rollback()
        if handled:
            return Response(exception_handler.error_data, status=exception_handler.response_status)

    def __init__(self, exception, context=None):
        self.error_objects = []
        self.error_data = {self.error_objects_key: self.error_objects}
        self.exception = exception
        self.response_headers = {}
        self.context = context

    def add_error_objects(self, obj):
        if isinstance(obj, (list, types.GeneratorType)):
            self.error_objects.extend(obj)
        else:
            self.error_objects.append(obj)

    def add_legacy_data(self, obj):
        self.error_data.update(obj)

    def process_exception(self):
        if isinstance(self.exception, APIErrorList):
            self.process_our_api_error_list()
        elif isinstance(self.exception, APIError):
            self.process_our_api_error()
        elif isinstance(self.exception, drf_exceptions.APIException):
            self.process_drf_exception()
        elif isinstance(self.exception, ValidationError):
            self.process_django_validation_error()
        elif isinstance(self.exception, Http404):
            self.process_http_404_error()
        elif isinstance(self.exception, PermissionDenied):
            self.process_permission_denied()
        else:
            return False
        return True

    def create_error_object(  # pylint: disable=R0913
        self, code, title, details=None, source=None, meta=None
    ):
        error_object = {'code': code, 'title': title}
        if details:
            error_object['details'] = details
        if source:
            error_object['source'] = source
        if meta:
            error_object['meta'] = meta
        return error_object

    def insert_error_object(self, **kwargs):
        error_object = self.create_error_object(**kwargs)
        self.add_error_objects(error_object)
        return error_object

    def _convert_field_errors_dict(self, errors):
        for field, error in errors.items():
            error_list = error if isinstance(error, list) else [error]
            for error_detail in error_list:
                error_object = self.create_error_object(
                    code='validation_error', title=error_detail, source={'parameter': field}
                )
                yield error_object

    def _convert_non_field_errors_list(self, code, errors):
        for error_detail in errors:
            yield self.create_error_object(code=code, title=error_detail)

    def _make_error_code(self):
        return decamelize(self.exception.__class__.__name__)

    ######

    def process_our_api_error(self):
        exception = self.exception
        self.insert_error_object(**exception.serialize())
        self.add_legacy_data(exception.get_legacy_data())
        self.response_status = exception.response_status

    def process_our_api_error_list(self):
        exception = self.exception
        self.add_error_objects(self.exception.serialize())
        self.add_legacy_data(exception.get_legacy_data())
        self.response_status = exception.response_status

    def process_http_404_error(self):
        self.insert_error_object(code='object_not_found', title=_('Объект не найден'))
        self.add_legacy_data({'detail': 'Not found'})
        self.response_status = status.HTTP_404_NOT_FOUND

    def process_permission_denied(self):
        title = self.exception.args[0] if self.exception.args else _('Доступ запрещен')
        self.insert_error_object(code='permission_denied', title=title)
        self.add_legacy_data({'detail': title})
        self.response_status = status.HTTP_403_FORBIDDEN

    def process_django_validation_error(self):
        exception = self.exception
        if hasattr(exception, 'error_dict'):
            self.add_error_objects(self._convert_field_errors_dict(exception.message_dict))
            self.add_legacy_data(exception.message_dict)
        else:
            self.add_error_objects(
                self._convert_non_field_errors_list('validation_error', exception.messages)
            )
            self.add_legacy_data({'non_field_errors': exception.messages})

    def process_drf_exception(self):
        drf_response = drf_exception_handler(self.exception, self.context)
        exception_data = drf_response.data
        # Hack-ish approach to snatch pre-rendered headers from DRF Response object
        self.response_headers.update(h[1] for h in drf_response._headers.items())
        self.response_status = self.exception.status_code
        if isinstance(exception_data, dict):
            self.add_legacy_data(exception_data)
            non_field_errors = exception_data.pop(api_settings.NON_FIELD_ERRORS_KEY, [])
            detail = exception_data.pop('detail', [])
            if not isinstance(detail, list):
                detail = [detail]
            non_field_errors.extend(detail)
            self.add_error_objects(self._convert_field_errors_dict(exception_data))
        elif isinstance(exception_data, list):
            non_field_errors = exception_data
            self.add_legacy_data({'non_field_errors': non_field_errors})
        else:
            non_field_errors = [exception_data]
            self.add_legacy_data({'non_field_errors': non_field_errors})
        self.add_error_objects(
            self._convert_non_field_errors_list(self._make_error_code(), non_field_errors)
        )


request_exception_handler = RequestExceptionHandler.handle
