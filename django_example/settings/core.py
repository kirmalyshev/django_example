# encoding=utf-8
# Core non project-related settings

from __future__ import unicode_literals

import logging
import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
from typing import Dict

SETTINGS_DIR = os.path.dirname(__file__)
BASE_DIR = os.path.abspath(os.path.join(SETTINGS_DIR, '..', '..'))
PROJECT_ROOT = os.path.abspath(os.path.dirname(SETTINGS_DIR))
PROJECT_NAME = os.path.basename(PROJECT_ROOT)
APPS_DIR = os.path.join(BASE_DIR, 'apps')

ALLOWED_HOSTS = ['*']

ENVIRONMENT_NAME = 'core'

ROOT_URLCONF = os.environ.get('ROOT_URLCONF', 'django_example.urls.common')

# Media settigns
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
if not os.path.exists(MEDIA_ROOT):
    os.makedirs(MEDIA_ROOT)
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
MEDIA_URL = '/media/'
STATIC_URL = '/static/'

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

# Applications
INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.admin',
    'django.contrib.staticfiles',
    'django.contrib.redirects',
    'django.contrib.humanize',
    'django.contrib.sites',
    'django.contrib.flatpages',
)

# Middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.locale.LocaleMiddleware',
]

# Base apps settings
MESSAGE_STORAGE = 'django.contrib.messages.storage.cookie.CookieStorage'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ]
        },
    }
]

WSGI_APPLICATION = 'django_example.wsgi.application'

# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

INTERNAL_IPS = ('127.0.0.1',)
TEST_SERVER = False
PRODUCTION_SERVER = False

ADMIN_PANEL_PATH = 'admin'

# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Logging
GRAYLOG_HOST = os.environ.get("GRAYLOG_HOST", 'localhost')
_CONSOLE = 'console'
NULL = 'null'
LOGGING: Dict = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
            # noqa
        },
        'simple': {'format': '%(levelname)s %(message)s'},
    },
    'filters': {'require_debug_false': {'()': 'django.utils.log.RequireDebugFalse'}},
    'handlers': {
        _CONSOLE: {'level': 'DEBUG', 'class': 'logging.StreamHandler', 'formatter': 'simple'},
        'console_warning': {
            'level': 'WARNING',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {'level': 'DEBUG', 'class': 'logging.FileHandler', 'filename': '/tmp/work.log'},
        NULL: {'level': 'DEBUG', 'class': 'logging.NullHandler'},
        # graylog handlers
        'graypy.notifications_graylog': {
            'level': 'INFO',
            'class': 'graypy.GELFUDPHandler',
            'host': GRAYLOG_HOST,
            'port': 12202,
        },
        'graypy.notifications_graylog__staging': {
            'level': 'INFO',
            'class': 'graypy.GELFUDPHandler',
            'host': GRAYLOG_HOST,
            'port': 12203,
        },
        'graypy.push_log_graylog': {
            'level': 'INFO',
            'class': 'graypy.GELFUDPHandler',
            'host': GRAYLOG_HOST,
            'port': 12204,
        },
        'graypy.push_log_graylog__staging': {
            'level': 'INFO',
            'class': 'graypy.GELFUDPHandler',
            'host': GRAYLOG_HOST,
            'port': 12205,
        },
        'graypy.import_log_graylog': {
            'level': 'WARNING',
            'class': 'graypy.GELFUDPHandler',
            'host': GRAYLOG_HOST,
            'port': 12206,
        },
        'graypy.one_time_login_log_graylog': {
            'level': 'INFO',
            'class': 'graypy.GELFUDPHandler',
            'host': GRAYLOG_HOST,
            'port': 12207,
        },
        'graypy.text_filtering_graylog': {
            'level': 'INFO',
            'class': 'graypy.GELFUDPHandler',
            'host': GRAYLOG_HOST,
            'port': 12208,
        },
        'graypy.celery': {
            'level': 'DEBUG',
            'class': 'graypy.GELFUDPHandler',
            'host': GRAYLOG_HOST,
            'port': 12209,
        },
        'graypy.google_analytics_graylog': {
            'level': 'INFO',
            'class': 'graypy.GELFUDPHandler',
            'host': GRAYLOG_HOST,
            'port': 12220,
        },
        'graypy.audit_log_graylog': {
            'level': 'INFO',
            'class': 'graypy.GELFUDPHandler',
            'host': GRAYLOG_HOST,
            'port': 12221,
        },
        'graypy.garbage': {
            'level': 'DEBUG',
            'class': 'graypy.GELFUDPHandler',
            'host': GRAYLOG_HOST,
            'port': 12299,
        },
    },
    'root': {'handlers': [_CONSOLE], 'level': 'DEBUG'},
    'loggers': {
        'root': {'handlers': [_CONSOLE], 'level': 'INFO', 'propagate': True},
        'django': {'handlers': [_CONSOLE], 'level': 'INFO', 'propagate': True},
        'joltem': {'handlers': [_CONSOLE], 'level': 'DEBUG', 'propagate': True},
        'tests': {'handlers': [_CONSOLE], 'level': 'DEBUG', 'propagate': True},
        # 'sentry.debug': {
        #     'level': 'DEBUG',
        #     'handlers': ['sentry'],
        #     'propagate': False,
        # },
        'factory': {'level': 'ERROR', 'handlers': [_CONSOLE], 'propagate': False},
        'requests': {'handlers': [_CONSOLE], 'level': 'ERROR', 'propagate': True},
        'iso8601.iso8601': {'level': 'ERROR', 'handlers': [_CONSOLE]},
        'urllib3.connectionpool': {'level': 'ERROR', 'handlers': [_CONSOLE]},
        'sorl.thumbnail.base': {'level': 'ERROR', 'handlers': [_CONSOLE]},
        'urllib3.util.retry': {'level': 'ERROR', 'handlers': [_CONSOLE], 'propagate': False},
        'requests.packages.urllib3.connectionpool': {
            'level': 'ERROR',
            'handlers': [_CONSOLE, 'file'],
            'propagate': False,
        },
        'deprecated': {'handlers': [_CONSOLE], 'level': 'WARNING', 'propagate': True,},
        'graylog.audit': {'handlers': [_CONSOLE], 'level': 'INFO', 'propagate': True,},
        'graylog.one_time_login': {'handlers': [_CONSOLE], 'level': 'INFO', 'propagate': True,},
        'graylog.notifications': {'handlers': [_CONSOLE], 'level': 'INFO', 'propagate': True,},
        'graylog.push_log': {'handlers': [_CONSOLE], 'level': 'INFO', 'propagate': True,},
        'api.warning': {'level': 'WARNING', 'handlers': [_CONSOLE], 'propagate': False,},
    },
}

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
    datefmt='%d.%m %H:%M:%S',
)
logging.info("Core settings loaded")
