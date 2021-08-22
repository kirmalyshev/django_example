# Settings for running via Docker
from .project import *
import os

# ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost 127.0.0.1").split(" ")
ALLOWED_HOSTS = ('*',)  # type: ignore

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.environ.get('DB_NAME', 'django_example_db'),
        'USER': os.environ.get('DB_USER', 'django_example_db_user'),
        'HOST': os.environ.get('DB_HOST', 'db'),
        'PORT': os.environ.get('DB_PORT', 5432),
        'ATOMIC_REQUESTS': True,
    }
}
password = os.environ.get('DB_PASSWORD')
if password:
    DATABASES['default']['PASSWORD'] = password

SESSION_COOKIE_DOMAIN = None

RECAPTCHA_ENABLED: bool = os.environ.get('RECAPTCHA_ENABLED', False)  # type: ignore


CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', f'redis://{REDIS_HOST}:{REDIS_PORT}/2')  # type: ignore
TEMPORARY_DATA_CONNECTION = os.environ.get('TEMPORARY_DATA_CONNECTION', f'redis://{REDIS_HOST}:{REDIS_PORT}/3')  # type: ignore
WS_STORAGE_DATA_CONNECTION = TEMPORARY_DATA_CONNECTION

EMAIL_HOST_FOR_SMS: str = 'mailhog'  # type: ignore
EMAIL_PORT_FOR_SMS: int = 1025  # type: ignore

LOGGING['loggers']['django']['handlers'] = ['console', 'console_warning']

print('settings.docker loaded')
