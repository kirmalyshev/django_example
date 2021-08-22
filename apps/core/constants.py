from typing import Dict

SYSTEM_SERVICE = 'System Service'


class SystemUserNames:
    ADMIN = 'admin@django_example.com'
    SYSTEM = 'system@django_example.com'
    VOXIMPLANT = 'system+voximplant@django_example.com'
    ONE_C = 'system+1c@django_example.com'
    INTEGRATION = 'system+integration@django_example.com'


EMPTY_STR = ''

RAISE_ERROR = "raise_error"

CREATED = "created"
MODIFIED = "modified"


class BaseStatus:
    VALUES: Dict[int, str] = {}

    @classmethod
    def get_display_value(cls, key):
        return cls.VALUES[key]

    VALUE_KEYS = VALUES.keys()

    CHOICES = VALUES.items()
