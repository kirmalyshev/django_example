# encoding=utf-8

from __future__ import print_function
from __future__ import unicode_literals

from django.conf import settings

from apps.profiles.factories import ProfileFactory
from apps.profiles.models import Profile

SKIP_FOR_TEST = True
HEAVY = False

DEPENDS_ON = []


def load():
    if not settings.TEST_SERVER:
        return
    if not Profile.objects.filter(is_approved_once=True).count() >= 300:
        ProfileFactory.create_batch(size=300, is_approved_once=True)
