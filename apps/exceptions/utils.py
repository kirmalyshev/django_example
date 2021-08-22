import re


DECAMELIZE_FIRST_RE = re.compile('(.)([A-Z][a-z]+)')
DECAMELIZE_SECOND_RE = re.compile('([a-z0-9])([A-Z])')


def decamelize(name):
    """
    Convert class names like APIError to api_error
    >>> decamelize("APIError")
    >>> "api_error"
    """
    return DECAMELIZE_SECOND_RE.sub(r'\1_\2', DECAMELIZE_FIRST_RE.sub(r'\1_\2', name)).lower()
