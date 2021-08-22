# encoding=utf-8

from __future__ import print_function
from __future__ import unicode_literals

from rest_framework import exceptions


class RedirectUrlError(exceptions.PermissionDenied):
    url = None

    def __init__(self, *args, **kwargs):
        self.url = kwargs.pop('url', None)
        super(RedirectUrlError, self).__init__(*args, **kwargs)
