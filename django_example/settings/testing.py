# encoding=utf-8
# Settings for test runs
# type: ignore

ENVIRONMENT_NAME = 'testing'

try:
    from .local import *
except ImportError:
    from .docker import *

TESTING = True
# INSTALLED_APPS += ('django_nose',)

SESSION_COOKIE_DOMAIN = 'localhost'

MEDIA_ROOT = os.path.join(BASE_DIR, 'test_media')

EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
SMS_BACKEND = 'apps.sms.backends.TestingBackend'

BASIC_AUTH = False

DEBUG = True

ALLOWED_HOSTS = ['127.0.0.1', 'localhost']
TEST_SERVER = False

SCSS_LINT_CONFIG_FILE = '.scss-lint.yml'

LOGGING = {
    'disable_existing_loggers': True,
    'version': 1,
    'loggers': {'': {'propagate': False}},
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
            # noqa
        },
        'simple': {'format': '%(message)s'},
    },
}

LOGGING['loggers'].update(
    {'urllib3.connectionpool': {'level': 'ERROR'}, 'urllib3.util.retry': {'level': 'ERROR'}}
)

# PROJECT_APPS += ('apps.moderation.tests',)
# INSTALLED_APPS += ('apps.moderation.tests',)

USE_AUDIT_LOG = False
USE_SPY_LOG = False
USE_NOTIFY_LOG = False

AUTO_OFFERS_COST_DATA_CONNECTION = (
    SERVICE_COST_DATA_CONNECTION
) = TEMPORARY_DATA_CONNECTION = CONSTANCE_REDIS_CONNECTION

CATALOG_STORAGE = {
    'elasticsearch_url': 'http://localhost:9200/',
    'indexes': ['test_catalog', 'test_spare_catalog'],
    'refresh_on_updates': True,
}

# CACHES['default']['KEY_PREFIX'] = "_".join((PROJECT_NAME, ENVIRONMENT_NAME))

FAKE_RECAPTCHA = True

URLSHORTENER_HOST = None

# TODO ОГРОООМНЫЙ костыль, чтобы авторизация через сессию была активна.
#  Нужно будет что-то с этим сделать
REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] = (
    'apps.auth.authenticate.ClinicTokenAuthentication',
    'rest_framework.authentication.BasicAuthentication',
    'rest_framework.authentication.SessionAuthentication',
)

REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['offers_create'] = '100/sec'
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['mobile_notifications_device__min'] = '100/sec'
