# from rest_framework import status
#
# from apps.core import case
#
# from apps.mobile_notifications import factories
# from apps.profiles.factories import UserFactory
#
#
# class APNSIntegrationTest_(case.SimpleDRFTest):
#     drf_urls = {
#         'create': 'api.v1:mobile_notifications:apns_devices',
#         'destroy': 'api.v1:mobile_notifications:apns_device_detail',
#     }
#
#     response_status_code = {
#         'list': status.HTTP_405_METHOD_NOT_ALLOWED,
#         'create': status.HTTP_201_CREATED,
#         'destroy': status.HTTP_204_NO_CONTENT,
#     }
#
#     create_param = {'registration_id': 'a' * 64}
#
#     password = "123"
#
#     lookup_url_kwarg = lookup_field = 'registration_id'
#
#     def factory(self):
#         return factories.APNSDeviceFactory(user=self.user)
#
#     @classmethod
#     def setUpTestData(cls):
#         cls.user = UserFactory(password=cls.password)
#         cls.username = cls.user.username
#
#
# class APNS2IntegrationTest_(APNSIntegrationTest_):
#     create_param = {'registration_id': 'a' * 64, 'application_id': 'django_example_ios_common'}
#
#
# class GCMIntegrationTest_(APNSIntegrationTest_):
#     drf_urls = {
#         'create': 'api.v1:mobile_notifications:gcm_devices',
#         'destroy': 'api.v1:mobile_notifications:gcm_device_detail',
#     }
#
#     create_param = {'registration_id': 'a'}
#
#     def factory(self):
#         return factories.GCMDeviceFactory(user=self.user)
#
#
# class GCM2IntegrationTest_(GCMIntegrationTest):
#     create_param = {'registration_id': 'a', 'application_id': 'django_example_android_common'}
