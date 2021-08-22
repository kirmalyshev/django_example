# import base64
# import json
# from uuid import uuid4
#
# import mock
# from django.contrib.auth.models import Group
# from django.urls import reverse
# from push_notifications.models import APNSDevice, GCMDevice
# from rest_framework import status
#
# from apps.clinics.factories import PatientUserFactory
# from apps.core.constants import SYSTEM_SERVICE
# from apps.core.test.utils import assert_signal_sent
# from apps.mobile_notifications.constants import FCM
# from apps.mobile_notifications.factories import GCMDeviceFactory, APNSDeviceFactory
# from apps.mobile_notifications.signals import push_notification_event_received
# from apps.profiles.constants import ProfileType
# from apps.profiles.factories import UserFactory
# from apps.tools.apply_tests.case import TestCaseCheckStatusCode
#
#
# class TestNotificationView(TestCaseCheckStatusCode):
#     url = reverse('api.v1:mobile_notifications:notifications')
#
#     def test_post(self):
#         profile = UserFactory().profile
#         system_group, _ = Group.objects.get_or_create(name=SYSTEM_SERVICE)
#         system_user = UserFactory(username='system@django_example.com', name=SYSTEM_SERVICE)
#         system_group.user_set.add(system_user)
#         self.client.force_login(system_user)
#         with mock.patch('apps.mobile_notifications.push.send_to_profile') as mock_send_to_profile:
#             response = self.client.post(
#                 self.url,
#                 {
#                     'profile': profile.pk,
#                     'message': json.dumps({'text': 'Test Message', 'some_key': 'some_key'}),
#                 },
#                 format='json',
#             )
#             self.check_status_code(response, status.HTTP_201_CREATED)
#             mock_send_to_profile.assert_called_once_with(
#                 profile=profile,
#                 message='Test Message',
#                 subject='Новое событие в Ремонтнике',
#                 payload={'some_key': 'some_key'},
#                 sender=system_user,
#                 sender_ip=mock.ANY,
#                 raise_error=mock.ANY,
#             )
#
#     def test_unauthorized_cannot_post(self):
#         response = self.client.post(self.url, {'profile': 1, 'message': 'Test Message'})
#         self.check_status_code(response, status.HTTP_401_UNAUTHORIZED)
#
#     def test_regular_user_cannot_post(self):
#         user = UserFactory(add_primary_phone=False, confirm_email=True)
#         self.client.force_login(user)
#         response = self.client.post(self.url, {'profile': 1, 'message': 'Test Message'},)
#         self.check_status_code(response, status.HTTP_401_UNAUTHORIZED)
#
#     def test_urls(self):
#         self.assertEqual(
#             reverse('api.v1:mobile_notifications:notifications'),
#             '/api/v1/mobile_notifications/notifications/',
#         )
#
#
# class GCMDeviceViewTest(TestCaseCheckStatusCode):
#     url = reverse('api.v1:mobile_notifications:gcm_devices')
#
#     def setUp(self):
#         self.user = UserFactory()
#
#     def test_register_user_is_authenticated_no_registered_device(self):
#         self.client.force_authenticate(user=self.user)
#         response = self.client.post(
#             self.url,
#             {'registration_id': 'test', 'name': 'Test gcm'},
#             HTTP_USER_AGENT='django_example for android 1.9.0',
#         )
#         self.check_status_code(response, status.HTTP_201_CREATED)
#         device = GCMDevice.objects.get(registration_id='test')
#         self.assertEqual(device.user, self.user)
#         self.assertEqual(device.name, 'Test gcm django_example for android 1.9.0')
#         self.assertTrue(device.active)
#
#     def test_register_user_is_authenticated_has_registered_device_with_user(self):
#         GCMDeviceFactory(
#             registration_id='test', user=self.user, name='Test gcm django_example for android 1.9.0'
#         )
#         self.client.force_authenticate(user=self.user)
#
#         response = self.client.post(
#             self.url,
#             {'registration_id': 'test', 'name': 'New name'},
#             HTTP_USER_AGENT='django_example for android 1.9.0',
#         )
#         self.check_status_code(response, status.HTTP_201_CREATED)
#         device = GCMDevice.objects.get(registration_id='test')
#         self.assertEqual(device.user, self.user)
#         self.assertEqual(device.name, 'New name django_example for android 1.9.0')
#         self.assertTrue(device.active)
#
#     def test_register_user_is_authenticated_has_registered_device_without_user(self):
#         GCMDeviceFactory(registration_id='test', user=None)
#         self.client.force_authenticate(user=self.user)
#
#         response = self.client.post(
#             self.url,
#             {'registration_id': 'test', 'name': 'Test gcm'},
#             HTTP_USER_AGENT='django_example for android 1.9.0',
#         )
#         self.check_status_code(response, status.HTTP_201_CREATED)
#         device = GCMDevice.objects.get(registration_id='test')
#         self.assertEqual(device.user, self.user)
#         self.assertEqual(device.name, 'Test gcm django_example for android 1.9.0')
#         self.assertTrue(device.active)
#
#     def test_register_user_is_not_authenticated_no_registered_device(self):
#         response = self.client.post(
#             self.url,
#             {'registration_id': 'test', 'name': 'Test gcm'},
#             HTTP_USER_AGENT='django_example for android 1.9.0',
#         )
#         self.check_status_code(response, status.HTTP_201_CREATED)
#         device = GCMDevice.objects.get(registration_id='test')
#         self.assertIsNone(device.user)
#         self.assertTrue(device.active)
#         self.assertEqual(device.name, 'Test gcm django_example for android 1.9.0')
#
#     def test_register_user_is_not_authenticated_has_registered_device_with_user(self):
#         GCMDeviceFactory(registration_id='test', user=self.user)
#
#         response = self.client.post(
#             self.url,
#             {'registration_id': 'test', 'name': 'Test gcm'},
#             HTTP_USER_AGENT='django_example for android 1.9.0',
#         )
#         self.check_status_code(response, status.HTTP_201_CREATED)
#         device = GCMDevice.objects.get(registration_id='test')
#         self.assertIsNone(device.user)
#         self.assertTrue(device.active)
#         self.assertEqual(device.name, 'Test gcm django_example for android 1.9.0')
#
#     def test_register_user_is_not_authenticated_has_registered_device_without_user(self):
#         GCMDeviceFactory(registration_id='test', user=None)
#
#         response = self.client.post(
#             self.url,
#             {'registration_id': 'test', 'name': 'Test gcm'},
#             HTTP_USER_AGENT='django_example for android 1.9.0',
#         )
#         self.check_status_code(response, status.HTTP_201_CREATED)
#         device = GCMDevice.objects.get(registration_id='test')
#         self.assertIsNone(device.user)
#         self.assertTrue(device.active)
#         self.assertEqual(device.name, 'Test gcm django_example for android 1.9.0')
#
#     def test_delete_own_device(self):
#         device = GCMDeviceFactory(registration_id='test', user=self.user)
#         self.client.force_authenticate(user=self.user)
#
#         url = reverse(
#             'api.v1:mobile_notifications:gcm_device_detail',
#             kwargs={'registration_id': device.registration_id},
#         )
#         response = self.client.delete(url)
#         self.check_status_code(response, status.HTTP_204_NO_CONTENT)
#         device = GCMDevice.objects.get(pk=device.pk)
#         self.assertIsNone(device.user)
#         self.assertTrue(device.active)
#
#         # send request one more time
#         response = self.client.delete(url)
#         self.check_status_code(response, status.HTTP_404_NOT_FOUND)
#
#     def test_delete_other_device(self):
#         device = GCMDeviceFactory(registration_id='test', user=UserFactory())
#         self.client.force_authenticate(user=self.user)
#
#         url = reverse(
#             'api.v1:mobile_notifications:gcm_device_detail',
#             kwargs={'registration_id': device.registration_id},
#         )
#         response = self.client.delete(url)
#         self.check_status_code(response, status.HTTP_404_NOT_FOUND)
#
#     def test_delete_not_authenticated_user_registered_device_with_user(self):
#         device = GCMDeviceFactory(registration_id='test', user=self.user)
#
#         url = reverse(
#             'api.v1:mobile_notifications:gcm_device_detail',
#             kwargs={'registration_id': device.registration_id},
#         )
#         response = self.client.delete(url)
#         self.check_status_code(response, status.HTTP_404_NOT_FOUND)
#
#     def test_delete_not_authenticated_user_registered_device_without_user(self):
#         device = GCMDeviceFactory(registration_id='test', user=None)
#
#         url = reverse(
#             'api.v1:mobile_notifications:gcm_device_detail',
#             kwargs={'registration_id': device.registration_id},
#         )
#         response = self.client.delete(url)
#         self.check_status_code(response, status.HTTP_404_NOT_FOUND)
#
#
# class FCMDeviceViewTest(GCMDeviceViewTest):
#     url = reverse('api.v1:mobile_notifications:fcm_devices')
#
#     def setUp(self):
#         self.user = UserFactory()
#
#     def test_register_user_is_authenticated_no_registered_device(self):
#         self.client.force_authenticate(user=self.user)
#         response = self.client.post(
#             self.url,
#             {'registration_id': 'test', 'name': 'Test fcm'},
#             HTTP_USER_AGENT='django_example for android 1.9.0',
#         )
#         self.check_status_code(response, status.HTTP_201_CREATED)
#         device = GCMDevice.objects.get(registration_id='test', cloud_message_type=FCM)
#         self.assertEqual(device.user, self.user)
#         self.assertEqual(device.name, 'Test fcm django_example for android 1.9.0')
#         self.assertTrue(device.active)
#
#
# class APNSDeviceViewTest(TestCaseCheckStatusCode):
#     url = reverse('api.v1:mobile_notifications:apns_devices')
#     registration_id = '579afEFC3F3e3e755fa2EA9e1Abf38e2d2AB6A794d182f9EcB6B8Eae4FA23AF4'
#
#     def setUp(self):
#         self.user = PatientUserFactory()
#
#     def test_register_user_is_authenticated_no_registered_device(self):
#         self.client.force_authenticate(user=self.user)
#
#         response = self.client.post(
#             self.url,
#             {'registration_id': self.registration_id, 'name': 'Test apns'},
#             HTTP_USER_AGENT='django_example for iOS 1.9.0',
#         )
#         self.check_status_code(response, status.HTTP_201_CREATED)
#         device = APNSDevice.objects.get(registration_id=self.registration_id)
#         self.assertEqual(device.user, self.user)
#         self.assertEqual(device.name, 'Test apns django_example for iOS 1.9.0')
#         self.assertTrue(device.active)
#
#     def test_register_user_is_authenticated_has_registered_device_with_user(self):
#         APNSDeviceFactory(
#             registration_id=self.registration_id,
#             user=self.user,
#             name='Test apns django_example for iOS 1.9.0',
#         )
#         self.client.force_authenticate(user=self.user)
#
#         response = self.client.post(
#             self.url,
#             {'registration_id': self.registration_id, 'name': 'New name'},
#             HTTP_USER_AGENT='django_example for iOS 1.9.0',
#         )
#         self.check_status_code(response, status.HTTP_201_CREATED)
#         device = APNSDevice.objects.get(registration_id=self.registration_id)
#         self.assertEqual(device.user, self.user)
#         self.assertEqual(device.name, 'New name django_example for iOS 1.9.0')
#         self.assertTrue(device.active)
#
#     def test_register_user_is_authenticated_has_registered_device_without_user(self):
#         APNSDeviceFactory(registration_id=self.registration_id, user=None)
#         self.client.force_authenticate(user=self.user)
#
#         response = self.client.post(
#             self.url,
#             {'registration_id': self.registration_id, 'name': 'Test apns'},
#             HTTP_USER_AGENT='django_example for iOS 1.9.0',
#         )
#         self.check_status_code(response, status.HTTP_201_CREATED)
#         device = APNSDevice.objects.get(registration_id=self.registration_id)
#         self.assertEqual(device.user, self.user)
#         self.assertEqual(device.name, 'Test apns django_example for iOS 1.9.0')
#         self.assertTrue(device.active)
#
#     def test_register_user_is_not_authenticated_no_registered_device(self):
#         response = self.client.post(
#             self.url,
#             {'registration_id': self.registration_id, 'name': 'Test apns'},
#             HTTP_USER_AGENT='django_example for iOS 1.9.0',
#         )
#         self.check_status_code(response, status.HTTP_201_CREATED)
#         device = APNSDevice.objects.get(registration_id=self.registration_id)
#         self.assertIsNone(device.user)
#         self.assertTrue(device.active)
#         self.assertEqual(device.name, 'Test apns django_example for iOS 1.9.0')
#
#     def test_register_user_is_not_authenticated_has_registered_device_with_user(self):
#         APNSDeviceFactory(registration_id=self.registration_id, user=self.user)
#
#         response = self.client.post(
#             self.url,
#             {'registration_id': self.registration_id, 'name': 'Test apns'},
#             HTTP_USER_AGENT='django_example for iOS 1.9.0',
#         )
#         self.check_status_code(response, status.HTTP_201_CREATED)
#         device = APNSDevice.objects.get(registration_id=self.registration_id)
#         self.assertIsNone(device.user)
#         self.assertTrue(device.active)
#         self.assertEqual(device.name, 'Test apns django_example for iOS 1.9.0')
#
#     def test_register_user_is_not_authenticated_has_registered_device_without_user(self):
#         APNSDeviceFactory(registration_id=self.registration_id, user=None)
#
#         response = self.client.post(
#             self.url,
#             {'registration_id': self.registration_id, 'name': 'Test apns'},
#             HTTP_USER_AGENT='django_example for iOS 1.9.0',
#         )
#         self.check_status_code(response, status.HTTP_201_CREATED)
#         device = APNSDevice.objects.get(registration_id=self.registration_id)
#         self.assertIsNone(device.user)
#         self.assertTrue(device.active)
#         self.assertEqual(device.name, 'Test apns django_example for iOS 1.9.0')
#
#     def test_delete_own_device(self):
#         device = APNSDeviceFactory(registration_id=self.registration_id, user=self.user)
#         self.client.force_authenticate(user=self.user)
#
#         url = reverse(
#             'api.v1:mobile_notifications:apns_device_detail',
#             kwargs={'registration_id': device.registration_id},
#         )
#         response = self.client.delete(url)
#         self.check_status_code(response, status.HTTP_204_NO_CONTENT)
#         device = APNSDevice.objects.get(pk=device.pk)
#         self.assertIsNone(device.user)
#         self.assertTrue(device.active)
#
#         # send request one more time
#         response = self.client.delete(url)
#         self.check_status_code(response, status.HTTP_404_NOT_FOUND)
#
#     def test_delete_other_device(self):
#         device = APNSDeviceFactory(registration_id=self.registration_id, user=UserFactory())
#         self.client.force_authenticate(user=self.user)
#
#         url = reverse(
#             'api.v1:mobile_notifications:apns_device_detail',
#             kwargs={'registration_id': device.registration_id},
#         )
#         response = self.client.delete(url)
#         self.check_status_code(response, status.HTTP_404_NOT_FOUND)
#
#     def test_delete_not_authenticated_user_registered_device_with_user(self):
#         device = APNSDeviceFactory(registration_id=self.registration_id, user=self.user)
#
#         url = reverse(
#             'api.v1:mobile_notifications:apns_device_detail',
#             kwargs={'registration_id': device.registration_id},
#         )
#         response = self.client.delete(url)
#         self.check_status_code(response, status.HTTP_404_NOT_FOUND)
#
#     def test_delete_not_authenticated_user_registered_device_without_user(self):
#         device = APNSDeviceFactory(registration_id=self.registration_id, user=None)
#
#         url = reverse(
#             'api.v1:mobile_notifications:apns_device_detail',
#             kwargs={'registration_id': device.registration_id},
#         )
#         response = self.client.delete(url)
#         self.check_status_code(response, status.HTTP_404_NOT_FOUND)
#
#
# class TestNotificationEventView(TestCaseCheckStatusCode):
#     def test_post(self):
#         push_uuid = str(uuid4())
#         url = reverse('api.v1:mobile_notifications:events', args=[push_uuid])
#         self.client.force_authenticate(UserFactory())
#
#         with assert_signal_sent(
#             push_notification_event_received,
#             push_uuid=push_uuid,
#             event_type='clicked',
#             event_labels=[{'a': 1}, {'b': 2}],
#         ):
#             response = self.client.post(
#                 url,
#                 data={
#                     'push_uuid': push_uuid,
#                     'type': 'clicked',
#                     'event_labels': [{'a': 1}, {'b': 2}],
#                 },
#                 format='json',
#             )
#
#         self.check_status_code(response, status.HTTP_200_OK)
