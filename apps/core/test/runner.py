# encoding=utf-8

import shutil

from django.conf import settings
from django.test.runner import DiscoverRunner


class MediaTeardownRunner(DiscoverRunner):
    """
    A custom test runner that destroys files left after testing models with FileFields.
    """

    def teardown_test_environment(self, **kwargs):
        super(MediaTeardownRunner, self).teardown_test_environment(**kwargs)
        # Precaution check in case we forgot to set a special testing directory
        if settings.TESTING and 'test' in settings.MEDIA_ROOT:
            try:
                shutil.rmtree(settings.MEDIA_ROOT)
            except OSError:
                pass
