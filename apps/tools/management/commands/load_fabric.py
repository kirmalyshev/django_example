# encoding=utf-8

import os
import sys

from django.conf import settings

from apps.core.decorators import run_if_setting_true
from apps.tools.management.commands._base_load_fabric import Command as LoadFabric

TESTING = 'test' in sys.argv


class Command(LoadFabric):
    _overridden_settings = {}

    def __init__(self, *args, **kwargs):
        # save settings
        self._overridden_settings['EMAIL_BACKEND'] = settings.EMAIL_BACKEND
        self._overridden_settings['SMS_BACKEND'] = settings.SMS_BACKEND
        self._overridden_settings['LOAD_FIXTURE_MODE'] = settings.LOAD_FIXTURE_MODE
        self._overridden_settings['GOOGLE_ANALYTICS_URLS'] = settings.GOOGLE_ANALYTICS_URLS

        # override settings
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
        settings.SMS_BACKEND = 'apps.sms.backends.MuteBackend'
        settings.LOAD_FIXTURE_MODE = True
        settings.GOOGLE_ANALYTICS_URLS = None

        super(Command, self).__init__(*args, **kwargs)

    def get_app_paths(self):
        """
        Retrieve application directories based on PROJECT_APPS
        """
        return sorted(
            [
                os.path.join(settings.BASE_DIR, name.replace('.', '/'), '')
                for name in settings.PROJECT_APPS
            ]
        )

    def handle(self, *args, **options):
        @run_if_setting_true('TEST_SERVER')
        def get_count_requests():
            from apps.moderation.models import ModerationRequest

            return ModerationRequest.objects.count()

        already_exists_request_count = get_count_requests() or 0

        try:
            super(Command, self).handle(*args, **options)
        except:
            self.revert_settings()
            raise

        # new moderated objects doesn`t exists after fixtures
        assert not ((get_count_requests() or 0) - already_exists_request_count)
        self.revert_settings()

    def revert_settings(self):
        for key, value in self._overridden_settings.items():
            setattr(settings, key, value)
