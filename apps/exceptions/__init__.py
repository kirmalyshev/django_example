# encoding=utf-8

from __future__ import unicode_literals
from __future__ import print_function

from rest_framework import status

from .utils import decamelize


class APIError(Exception):
    code = None
    title = 'API Error'
    details = None
    response_status = status.HTTP_400_BAD_REQUEST

    def __init__(self, title=None, code=None, details=None, **kwargs):
        if title:
            self.title = title
        if code:
            self.code = code
        elif not self.code:
            self.code = decamelize(self.__class__.__name__)
        self.source = kwargs.pop('source', None)
        if details:
            self.details = details
        self.meta = {}
        self.meta.update(kwargs)

    def serialize(self):
        error_dict = {'code': self.code, 'title': self.title}
        if isinstance(self.source, dict):
            error_dict['source'] = self.source
        elif self.source:
            error_dict['source'] = {'parameter': self.source}
        if self.meta:
            error_dict['meta'] = self.meta
        if self.details:
            error_dict['details'] = self.details
        return error_dict

    def get_legacy_data(self):
        return {}

    def __str__(self):
        return '[{}] {}'.format(self.code, self.title)


class APIErrorList(APIError):
    """
    Return multiple errors in one `raise`. Supplied exceptions have to be APIError instances.

    Usage:

    APIErrorList([APIError(...), APIError(...)])
    """

    code = None
    title = 'API Errors'
    response_status = status.HTTP_400_BAD_REQUEST

    def __init__(self, error_list):
        for error_instance in error_list:
            assert isinstance(
                error_instance, APIError
            ), 'Supplied exceptions have to be APIError instances'
        self.error_list = error_list

    def serialize(self):
        for error in self.error_list:
            yield error.serialize()
