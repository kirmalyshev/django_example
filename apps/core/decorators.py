# encoding=utf-8

from functools import wraps

from django.conf import settings


def run_if_setting_true(setting_name):
    """
    Check if setting_name is set in django conf and is not false,
    otherwise do not run a decorated function
    """

    def decorate(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            setting = getattr(settings, setting_name, False)
            if setting:
                return func(*args, **kwargs)

        return wrapper

    return decorate


def run_if_setting_false(setting_name):
    """
    Check if setting_name is not set in django conf or is false,
    otherwise do not run a decorated function
    """

    def decorate(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not getattr(settings, setting_name, False):
                return func(*args, **kwargs)

        return wrapper

    return decorate


def mute_errors(func):
    """
    Silent run function and log exception into sentry
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        if settings.TESTING:
            return func(*args, **kwargs)

        try:
            result = func(*args, **kwargs)
        except Exception as err:
            # RecordLog('sentry.debug').error(err.args if err.args else tuple())
            result = None
        return result

    return wrapper
