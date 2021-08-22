import string

import factory
from django.conf import settings
from factory import fuzzy

from apps.mobile_notifications.constants import GCM, FCM
from apps.profiles.factories import UserFactory


class DeviceFactory(factory.django.DjangoModelFactory):
    class Meta:
        abstract = True

    user = factory.SubFactory(UserFactory)
    name = fuzzy.FuzzyText(length=10)
    registration_id = fuzzy.FuzzyText(length=64, chars=string.hexdigits)


class GCMDeviceFactory(DeviceFactory):
    class Meta:
        model = 'push_notifications.GCMDevice'

    application_id = settings.GCM_DEFAULT_APPLICATION_ID
    cloud_message_type = fuzzy.FuzzyChoice((FCM, GCM))


class APNSDeviceFactory(DeviceFactory):
    class Meta:
        model = 'push_notifications.APNSDevice'

    application_id = settings.APNS_DEFAULT_APPLICATION_ID
