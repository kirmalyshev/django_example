# encoding=utf-8

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.core.cache import cache
from django.core.cache.backends.base import DEFAULT_TIMEOUT


def get_or_calculate(key, calculator_function, timeout=None, args=None, kwargs=None):
    """
    Try to get the requested key from cache,
    retrieve and store from calculator_function called with args and kwargs
    if the key is not present.
    """
    args = args or []
    kwargs = kwargs or {}
    timeout = timeout or DEFAULT_TIMEOUT
    value = cache.get(key)
    if value is None:
        value = calculator_function(*args, **kwargs)
        cache.set(key, value, timeout=timeout)
    return value
