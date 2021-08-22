# from django.conf import settings
# from django.test import RequestFactory, TestCase, override_settings
#
# from apps.mobile_notifications.serializers import GCMDeviceSerializer, APNSDeviceSerializer
#
#
# class TestGCMDeviceSerializer(TestCase):
#     @override_settings(GCM_DEFAULT_APPLICATION_ID='django_example_android_common')
#     def test_validate_application_id(self):
#         default_application_id = settings.GCM_DEFAULT_APPLICATION_ID
#         valid_application_id = 'android_customer'
#         invalid_application_id = valid_application_id[::-1]
#         registration_id = 'abc'
#
#         serializer = GCMDeviceSerializer(data={'name': 'test', 'registration_id': registration_id,})
#         self.assertTrue(serializer.is_valid())
#         self.assertEqual(serializer.validated_data['application_id'], default_application_id)
#
#         serializer = GCMDeviceSerializer(
#             data={
#                 'name': 'test',
#                 'registration_id': registration_id,
#                 'application_id': valid_application_id,
#             }
#         )
#         self.assertTrue(serializer.is_valid())
#
#         serializer = GCMDeviceSerializer(
#             data={
#                 'name': 'test',
#                 'registration_id': registration_id,
#                 'application_id': invalid_application_id,
#             }
#         )
#         self.assertFalse(serializer.is_valid())
#         self.assertIn('application_id', serializer.errors)
#
#     def test_valid_device_id(self):
#         request = RequestFactory().get('/')
#
#         valid_device_id = '014AEC092FA74D78'
#         invalid_device_id = 'eZ1nE8t50is'
#         registration_id = 'abc'
#         serializer = GCMDeviceSerializer(
#             data={
#                 'name': 'test',
#                 'device_id': valid_device_id,
#                 'registration_id': registration_id,
#             },
#             context={'request': request},
#         )
#         self.assertTrue(serializer.is_valid())
#
#         serializer = GCMDeviceSerializer(
#             data={
#                 'name': 'test',
#                 'device_id': invalid_device_id,
#                 'registration_id': registration_id,
#             },
#             context={'request': request},
#         )
#         self.assertFalse(serializer.is_valid())
#         self.assertIn('device_id', serializer.errors)
#
#
# class TestAPNSDeviceSerializer(TestCase):
#     def test_validate_registration_id(self):
#         valid_registration_id = '579afEFC3F3e3e755fa2EA9e1Abf38e2d2AB6A794d182f9EcB6B8Eae4FA23AF4'
#         invalid_registration_id = '5_9afEFC3F3e3e755fa2EA9e1Abf38e2d2AB6A794d182f9EcB6B8Eae4FA23AF4'
#         serializer = APNSDeviceSerializer(
#             data={'name': 'test', 'registration_id': valid_registration_id}
#         )
#         self.assertTrue(serializer.is_valid())
#
#         serializer = APNSDeviceSerializer(
#             data={'name': 'test', 'registration_id': invalid_registration_id}
#         )
#         self.assertFalse(serializer.is_valid())
#         self.assertIn('registration_id', serializer.errors)
