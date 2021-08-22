# Project-specific settings, common for all machines hosting it
import socket
from collections import OrderedDict
from typing import List

import sentry_sdk
from kombu import Exchange, Queue
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.redis import RedisIntegration

try:
    from django_example.version import django_example_version

    CURRENT_VERSION = django_example_version
except:
    CURRENT_VERSION = '-1.0.0'

from .core import *

# Debug
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = bool(os.environ.get('DJANGO_DEBUG', False))

TESTING = False

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'some_key')

LANGUAGE_CODE = 'ru-RU'
TIME_ZONE = os.environ.get('TIME_ZONE', 'Europe/Moscow')

STATICFILES_DIRS = (os.path.join(PROJECT_ROOT, 'static'), os.path.join(PROJECT_ROOT, 'components'))

PROJECT_APPS = (
    'apps.core.apps.CoreConfig',
    'apps.sms',
    'apps.notify',
    'apps.profiles.apps.ProfilesConfig',
    'apps.clinics.apps.ClinicsConfig',
    'apps.appointments.apps.AppointmentsConfig',
    'apps.mobile_notifications.app.MobileNotificationsConfig',
    'apps.support',
    'apps.reviews',
)

SYSTEM_APPS = (
    'django_extensions',
    'rest_framework',
    'rest_framework.authtoken',
    'drf_yasg',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    # ... include the providers you want to enable:
    'allauth.socialaccount.providers.auth0',
    'allauth.socialaccount.providers.facebook',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.instagram',
    'allauth.socialaccount.providers.kakao',
    'allauth.socialaccount.providers.mailru',
    'allauth.socialaccount.providers.odnoklassniki',
    'allauth.socialaccount.providers.orcid',
    'allauth.socialaccount.providers.persona',
    'allauth.socialaccount.providers.pinterest',
    'allauth.socialaccount.providers.twitter',
    'allauth.socialaccount.providers.vk',
    'rest_auth',
    'rest_auth.registration',
    'mptt',
    'constance',
    'sorl.thumbnail',
    "push_notifications",
    'corsheaders',
    'ckeditor',
    'channels',
    'celery',
    "easyaudit",
    "csvexport",
)

INSTALLED_APPS += SYSTEM_APPS + PROJECT_APPS + ('apps.tools',)

AUTH_USER_MODEL = 'profiles.User'

PAGINATION_DEFAULT_MARGIN = 0
PAGINATION_DEFAULT_WINDOW = 4
PAGINATION_DISPLAY_DISABLED_PREVIOUS_LINK = True
PAGINATION_DISPLAY_DISABLED_NEXT_LINK = True

SITE_ID = 1

SESSION_COOKIE_NAME = 'django_example_sessionid'
SESSION_SERIALIZER = 'django.contrib.sessions.serializers.PickleSerializer'
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'

# region REST Framework
REST_FRAMEWORK = {
    # Use hyperlinked styles by default.
    # Only used if the `serializer_class` attribute is not set on a view.
    'DEFAULT_MODEL_SERIALIZER_CLASS': 'rest_framework.serializers.HyperlinkedModelSerializer',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'apps.auth.authenticate.ClinicTokenAuthentication',
        'rest_framework.authentication.BasicAuthentication',
        # 'rest_framework.authentication.SessionAuthentication',
    ),
    'EXCEPTION_HANDLER': 'apps.exceptions.handlers.request_exception_handler',
    'DEFAULT_THROTTLE_CLASSES': ('rest_framework.throttling.ScopedRateThrottle',),
    'DEFAULT_THROTTLE_RATES': {
        'get_token_or_register': os.environ.get('THROTTLE__GET_TOKEN_OR_REGISTER', '10/min'),
        'sms_token_login': os.environ.get('THROTTLE__SMS_TOKEN_LOGIN', '10/min'),
        'create_appointment_request': os.environ.get(
            'THROTTLE__CREATE_APPOINTMENT_REQUEST', '1/min'
        ),
        'mobile_notifications_device': '100/day',
        'mobile_notifications_device__min': '1/min',
        'mobile_notifications_device__max': '100/day',
        "create_support_request": os.environ.get('THROTTLE__CREATE_SUPPORT_REQUEST', '1/min'),
        "simple_confirm_phone": os.environ.get('THROTTLE__SIMPLE_CONFIRM_PHONE', '10/day'),
    },
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 100,
}
DEFAULT_PAGE_SIZE = 50
REST_AUTH_SERIALIZERS = {
    'USER_DETAILS_SERIALIZER': 'apps.profiles.serializers.ClinicUserDetailsSerializer'
}
REST_FRAMEWORK_EXTENSIONS = {'DEFAULT_CACHE_ERRORS': False}
# endregion

MIDDLEWARE.extend(
    [
        'django.contrib.redirects.middleware.RedirectFallbackMiddleware',
        'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
        'apps.core.middleware.HttpClientMiddleware',
        'easyaudit.middleware.easyaudit.EasyAuditMiddleware',
    ]
)


def is_installed_debug_toolbar() -> bool:
    try:
        import debug_toolbar

        return True
    except ImportError:
        return False


DEBUG_TOOLBAR_ON = DEBUG and os.environ.get("DEBUG_TOOLBAR_ON") and is_installed_debug_toolbar()
if DEBUG_TOOLBAR_ON:
    INSTALLED_APPS = INSTALLED_APPS + ('debug_toolbar',)
    MIDDLEWARE.extend(
        ['debug_toolbar.middleware.DebugToolbarMiddleware',]
    )
    hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
    INTERNAL_IPS = [ip[:-1] + '1' for ip in ips] + ['127.0.0.1', '10.0.2.2']

    DEBUG_TOOLBAR_PANELS = [
        'debug_toolbar.panels.versions.VersionsPanel',
        'debug_toolbar.panels.timer.TimerPanel',
        'debug_toolbar.panels.settings.SettingsPanel',
        'debug_toolbar.panels.headers.HeadersPanel',
        'debug_toolbar.panels.request.RequestPanel',
        'debug_toolbar.panels.sql.SQLPanel',
        'debug_toolbar.panels.staticfiles.StaticFilesPanel',
        'debug_toolbar.panels.templates.TemplatesPanel',
        'debug_toolbar.panels.cache.CachePanel',
        'debug_toolbar.panels.signals.SignalsPanel',
        'debug_toolbar.panels.logging.LoggingPanel',
        'debug_toolbar.panels.redirects.RedirectsPanel',
        'debug_toolbar.panels.profiling.ProfilingPanel',
    ]

# region logging
USE_NOTIFY_LOG = bool(os.environ.get('USE_NOTIFY_LOG', False))
LOGGING['loggers'].update(
    {
        'graylog.notifications': {
            'handlers': [os.environ.get('NOTIFICATIONS_LOG_HANDLER', 'null')],
            'level': 'INFO',
            'propagate': True,
        },
        'graylog.push_log': {
            'handlers': [os.environ.get('PUSH_LOG_HANDLER', 'null')],
            'level': 'INFO',
            'propagate': True,
        },
        'graylog.google_analytics': {
            'handlers': [os.environ.get('GOOGLE_ANALYTICS_LOG_HANDLER', default='null')],
            'level': 'INFO',
            'propagate': True,
        },
        'graylog.audit': {
            'handlers': [
                # os.environ.get('AUDIT_LOG_HANDLER', 'null')
            ],
            'level': 'INFO',
            'propagate': True,
        },
        'graylog.one_time_login': {
            'handlers': [
                # os.environ.get('ONE_TIME_LOGIN_LOG_HANDLER', 'null')
            ],
            'level': 'INFO',
            'propagate': True,
        },
        # 'graylog.text_filtering': {
        #     'handlers': [os.environ.get('TEXT_FILTERING_LOG_HANDLER', 'null')],
        #     'level': 'INFO',
        #     'propagate': True,
        # },
        'deprecated': {
            'handlers': [os.environ.get('DEPRECATED_LOG_HANDLER', 'null')],
            'level': 'WARNING',
            'propagate': True,
        },
    }
)

celery_log_handler = os.environ.get('CELERY_LOG_HANDLER')
if celery_log_handler:
    CELERYD_HIJACK_ROOT_LOGGER = False
    LOGGING['loggers']['celery'] = {
        'handlers': [celery_log_handler],
        'level': 'INFO',
        'propagate': False,
    }
# endregion

REGISTRATION_SUPPORT_TIMEOUT_SECONDS = 300
PRIMARY_PHONE_CONFIRM_AND_CHANGE_TIMEOUT = 300
PRIMARY_PHONE_CHANGE_DELAY_DAYS = 14

AUTHENTICATION_BACKENDS = (
    'apps.auth.backends.OnlyPhoneBackend',
    'django.contrib.auth.backends.ModelBackend',
)

LOGOUT_REDIRECT_URL = f'/{ADMIN_PANEL_PATH}'

DATE_FORMATTER = "d E Y г. H:i"
DATE_FORMATTER_SHORT = "d E Y г."
TIME_DATE_FORMATTER = "H:i, d E Y г"
DATE_FORMATTER_MONTH_YEAR = "E Y г."
DATETIME_DATE_FORMAT = '%d.%m.%Y'

REDIS_HOST = os.environ.get('REDIS_HOST', 'redis')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))

# region Constance
CONSTANCE_REDIS_CONNECTION = f'redis://{REDIS_HOST}:{REDIS_PORT}/1'

CONSTANCE_CONFIG_DICT = {
}

CONSTANCE_CONFIG = OrderedDict(sorted(CONSTANCE_CONFIG_DICT.items(), key=lambda x: x[0]))
CONSTANCE_CONFIG_FIELDSETS = OrderedDict(
)

# Constance variables in public access
PUBLIC_CONSTANCE_VARS: List[str] = []
CLINIC_INFO_CONSTANCE_VARS: List[str] = [
    'CLINIC_INFO_TEXT',
]

# endregion

PREFIX_URL = os.environ.get('PREFIX_URL', 'https://django_example.com')
SHORT_PREFIX = PREFIX_URL.replace("http://", '').replace("https://", '')

TEMPORARY_DATA_CONNECTION = None

# region Celery
CELERY_APP = 'django_example.celery:app'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERYD_MAX_TASKS_PER_CHILD = 20
CELERYD_TASK_SOFT_TIME_LIMIT = 10.0 * 60  # max 10 minutes per task
CELERY_IGNORE_RESULT = False

CELERY_QUEUES = (
    Queue('high', Exchange('high'), routing_key='high'),
    Queue('normal', Exchange('normal'), routing_key='normal'),
    Queue('low', Exchange('low'), routing_key='low'),
)

CELERY_DEFAULT_QUEUE = 'normal'
CELERY_DEFAULT_EXCHANGE = 'normal'
CELERY_DEFAULT_ROUTING_KEY = 'normal'
# endregion

LOCALE_PATHS = (os.path.join(BASE_DIR, 'locale'),)

# region Email
EMAIL_HOST = os.environ.get('EMAIL_HOST')
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
EMAIL_PORT = os.environ.get('EMAIL_PORT')
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', True)

DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'django_example Robot <no_reply@django_example.com>')
SYSTEM_SENDER_EMAIL = os.environ.get(
    'SYSTEM_SENDER_EMAIL', 'django_example Sender <email_sender@django_example.com>'
)
DEFAULT_ADMIN_EMAIL = 'admin@django_example.com'
FAQ_SUPPORT_EMAIL = 'support@django_example.com'
# endregion

# region SMS
SMS_BACKEND_PARAMS = {
    'GATEWAY_URL': os.environ.get("SMS_GATEWAY_URL"),
    'GATEWAY_LOGIN': os.environ.get("SMS_GATEWAY_LOGIN"),
    'GATEWAY_PASSWORD': os.environ.get("SMS_GATEWAY_PASSWORD"),
    'SENDER': os.environ.get("SMS_SENDER"),
}
SMS_LOGIN_TIMEOUT = 300
SMS_DEFAULT_TEMPLATE = ''
SMS_BACKEND = 'apps.sms.backends.SmsAsEmailBackend'  # via Mailhog
ENV_SMS_BACKEND = os.environ.get('SMS_BACKEND')
REAL_SMS_ENABLED = os.environ.get('REAL_SMS_ENABLED', False)
if REAL_SMS_ENABLED:
    SMS_BACKEND = ENV_SMS_BACKEND or 'apps.sms.backends.HttpBackend'

EMAIL_HOST_FOR_SMS = ''
EMAIL_PORT_FOR_SMS = ''
SMS_AS_EMAIL_RECIPIENT = 'sms_recipient@django_example.com'
# endregion

BASIC_AUTH = False

MIN_PASSWORD_LENGTH = 6

LOAD_FIXTURE_MODE = False

MAX_IMAGE_ORIGINAL_SIZE = (2048, 2048)

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

CORS_REPLACE_HTTPS_REFERER = True

GOOGLE_ANALYTICS_URLS = None
GOOGLE_ANALYTICS_SITE_ID = 'some_tid'

RECAPTCHA_ENABLED = True
FAKE_RECAPTCHA = True
RECAPTCHA_API_URL = 'https://www.google.com/recaptcha/api/siteverify'
RECAPTCHA_PUBLIC_KEY = 'public_key'
RECAPTCHA_PRIVATE_KEY = 'private_key'


# Changing Company Information
# offset-naive datetime (with timezone)
TEMPORARY_COMPANY_INFO: Dict = {}

BANKS: Dict = {}

URLSHORTENER_HOST = 'https://shortener.org/'
URLSHORTENER_TOKEN = 'auth-token-string'

NOSE_ARGS = ['--nocapture']
TEST_RUNNER = 'apps.core.test.runner.MediaTeardownRunner'

# region Sentry
SENTRY_PROJECT_ID = os.environ.get('SENTRY_PROJECT_ID')
SENTRY_TOKEN = os.environ.get('SENTRY_TOKEN')
if SENTRY_PROJECT_ID and SENTRY_TOKEN:
    sentry_sdk.init(
        dsn=f"https://{SENTRY_TOKEN}@sentry.io/{SENTRY_PROJECT_ID}",
        integrations=[DjangoIntegration(), CeleryIntegration(), RedisIntegration()],
        environment=os.environ.get("SENTRY_ENVIRONMENT", None),
        send_default_pii=True,
    )
# endregion

ASGI_APPLICATION = "apps.clinics.routing.application"
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {"hosts": [(REDIS_HOST, REDIS_PORT)],},
    },
}

# region Push notifications
GCM_DEFAULT_APPLICATION_ID = os.environ['GCM_DEFAULT_APPLICATION_ID']
APNS_DEFAULT_APPLICATION_ID = os.environ['APNS_DEFAULT_APPLICATION_ID']

MOBILE_APPS_LINKS = {
    GCM_DEFAULT_APPLICATION_ID: f"https://play.google.com/store/apps/details?id="
    f"{os.environ.get('GOOGLE_DEFAULT_APPLICATION_STORE_ID')}",
    APNS_DEFAULT_APPLICATION_ID: f"https://apps.apple.com/ru/app/{os.environ.get('APPLE_DEFAULT_APPLICATION_STORE_ID')}",
}

APNS_CERTIFICATE_FILENAME = os.environ.get('APNS_CERTIFICATE_NAME')
FCM_API_KEY = os.environ.get('FCM_API_KEY')
GCM_API_KEY = os.environ.get('GCM_API_KEY')
PUSH_NOTIFICATIONS_SETTINGS = {
    'CONFIG': 'push_notifications.conf.AppConfig',
    'APPLICATIONS': {
        GCM_DEFAULT_APPLICATION_ID: {
            'PLATFORM': 'FCM',
            'API_KEY': f"{FCM_API_KEY}",
            'ERROR_TIMEOUT': 15,
        },
        APNS_DEFAULT_APPLICATION_ID: {
            'PLATFORM': 'FCM',
            'API_KEY': f"{FCM_API_KEY}",
            'ERROR_TIMEOUT': 15,
            #     'PLATFORM': 'APNS',
            #     'CERTIFICATE': str(os.path.join(BASE_DIR, f"certs/{APNS_CERTIFICATE_FILENAME}")),
            #     # based tcp socket server
            #     # if isn`t None, wait answer on server
            #     # ignore APNS result
            #     'USE_SANDBOX': True,
            #     'TOPIC': 'ru.django_exampleapp.django_exampleapp',
        },
    },
}
# endregion

# region Feature Toggles
CLIENT_CONFIG_DIR = os.path.join(BASE_DIR, 'client_config')
if not os.path.exists(CLIENT_CONFIG_DIR):
    os.makedirs(CLIENT_CONFIG_DIR)
# here defined features for client configurations.
# Every feature = block/module, which can be sold to client as independent module
OPS_FEATURES = {
    'is_reviews_enabled': os.environ.get('FEATURE__IS_REVIEWS_ENABLED', False),
    'is_bonuses_enabled': os.environ.get('FEATURE__IS_BONUSES_ENABLED', False),
    'is_payment_in_app_enabled': os.environ.get('FEATURE__IS_PAYMENT_IN_APP_ENABLED', False),
    'assignments_available_for_patient': os.environ.get(
        'FEATURE__ASSIGNMENTS_AVAILABLE_FOR_PATIENT', False
    ),
    'django_admin__can_generate_timeslots': os.environ.get(
        "FEATURE__DJANGO_ADMIN__CAN_GENERATE_DOCTOR_TIMESLOTS", False
    ),
    'way_to_see_doctors_in_app': os.environ.get('FEATURE__WAY_TO_SEE_DOCTORS_IN_APP', None),
}
# endregion

DJANGO_EASY_AUDIT_WATCH_MODEL_EVENTS = True
DJANGO_EASY_AUDIT_WATCH_AUTH_EVENTS = True
DJANGO_EASY_AUDIT_WATCH_REQUEST_EVENTS = False
DJANGO_EASY_AUDIT_ADMIN_SHOW_REQUEST_EVENTS = False
DJANGO_EASY_AUDIT_UNREGISTERED_CLASSES_EXTRA = ["mobile_notifications.PushLog", "sms.SMSCode"]
# DJANGO_EASY_AUDIT_CRUD_DIFFERENCE_CALLBACKS = ["apps.tools.easyaudit_custom.tmp_callback"]
DJANGO_EASY_AUDIT_UNREGISTERED_URLS_DEFAULT = [r'^/admin/']
