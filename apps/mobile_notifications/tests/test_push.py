# import re
#
# import mock
# from django.conf import settings
# from django.test import TestCase
# from push_notifications.models import GCMDevice, APNSDevice
#
# from apps.core.test.utils import assert_signal_sent, assert_signal_not_sent
# from apps.notify.models import Event
# from apps.profiles.factories import UserFactory, ProfileFactory
# from apps.mobile_notifications import push
# from apps.mobile_notifications.factories import APNSDeviceFactory, GCMDeviceFactory
# from apps.mobile_notifications.signals import push_notification_sent
#
#
# class PushTest(TestCase):
#     @classmethod
#     def setUpTestData(cls):
#         cls.user = UserFactory()
#         cls.profile = ProfileFactory()
#         cls.user.profile = cls.profile
#
#     def test_send_to_profile(self, *args, **kwargs):
#         gcm_device = GCMDeviceFactory(user=self.user)
#         with mock.patch('push_notifications.models.GCMDevice.send_message') as gcm_send_mock:
#             push.send_to_profile(
#                 profile=self.user.profile, message='Test Message', subject='Test Subject'
#             )
#             gcm_send_mock.assert_called_once_with(
#                 message=None,
#                 extra={
#                     'caption': 'Test Subject',
#                     'message': {'text': 'Test Message', 'target_screen': 'default',},
#                     'text': 'Test Message',
#                     'uuid': mock.ANY,
#                     'target_screen': 'default',
#                 },
#             )
#             gcm_send_mock.reset_mock()
#             apns_device = APNSDeviceFactory(user=self.user)
#             with mock.patch('push_notifications.models.APNSDevice.send_message') as apns_send_mock:
#                 push.send_to_profile(
#                     profile=self.user.profile, message='Test Message', subject='Test Subject'
#                 )
#                 gcm_send_mock.assert_called_once_with(
#                     message=None,
#                     extra={
#                         'caption': 'Test Subject',
#                         'message': {'text': 'Test Message', 'target_screen': 'default',},
#                         'text': 'Test Message',
#                         'uuid': mock.ANY,
#                         'target_screen': 'default',
#                     },
#                 )
#                 apns_send_mock.assert_called_once_with(
#                     badge=1,
#                     sound='default',
#                     mutable_content=1,
#                     message={'title': 'Test Subject', 'body': 'Test Message',},
#                     extra={'uuid': mock.ANY, 'payload': {'target_screen': 'default',},},
#                 )
#
#     def test_send_text_message(self, *args, **kwargs):
#         gcm_device = GCMDeviceFactory(user=self.user)
#         with mock.patch('push_notifications.models.GCMDevice.send_message') as gcm_send_mock:
#             push.send_to_profile(
#                 profile=self.user.profile.pk, message='Test Message', subject='Test Subject'
#             )
#             gcm_send_mock.assert_called_once_with(
#                 message=None,
#                 extra={
#                     'caption': 'Test Subject',
#                     'message': {'text': 'Test Message', 'target_screen': 'default',},
#                     'text': 'Test Message',
#                     'uuid': mock.ANY,
#                     'target_screen': 'default',
#                 },
#             )
#
#     def test_send_dumped_json(self, *args, **kwargs):
#         gcm_device = GCMDeviceFactory(user=self.user)
#         with mock.patch('push_notifications.models.GCMDevice.send_message') as gcm_send_mock:
#             push.send_to_profile(
#                 profile=self.user.profile.pk, message='Test Message', subject='Test Subject'
#             )
#             gcm_send_mock.assert_called_once_with(
#                 message=None,
#                 extra={
#                     'caption': 'Test Subject',
#                     'message': {'text': 'Test Message', 'target_screen': 'default',},
#                     'text': 'Test Message',
#                     'uuid': mock.ANY,
#                     'target_screen': 'default',
#                 },
#             )
#
#     def test_send_to_profile_raise_error(self):
#         GCMDeviceFactory(user=self.user)
#         with mock.patch('push_notifications.models.GCMDevice.send_message') as gcm_send_mock:
#             gcm_send_mock.side_effect = push.GCMError('TestRaise')
#             with self.assertRaises(push.GCMError):
#                 push.send_to_profile(
#                     profile=self.user.profile,
#                     message='Test Message',
#                     subject='Test Subject',
#                     raise_error=True,
#                 )
#
#     def test_send_to_profile_raise_error_silent(self):
#         GCMDeviceFactory(user=self.user)
#         with mock.patch('push_notifications.models.GCMDevice.send_message') as gcm_send_mock:
#             gcm_send_mock.side_effect = push.GCMError('TestRaise')
#             push.send_to_profile(
#                 profile=self.user.profile,
#                 message='Test Message',
#                 subject='Test Subject',
#                 raise_error=False,
#             )
#
#     def test_send_to_not_multipart_registered_gcm_device(self):
#         with mock.patch('push_notifications.models.GCMDevice.send_message') as gcm_send_mock:
#             gcm_send_mock.side_effect = push.GCMError('NotRegistered')
#             gcm_device = GCMDeviceFactory(user=self.user)
#             push.send_to_profile(
#                 profile=self.user.profile,
#                 message='Test Message',
#                 subject='Test Subject',
#                 raise_error=False,
#             )
#             self.assertFalse(gcm_device.__class__.objects.get(pk=gcm_device.pk).active)
#
#     def test_send_to_not_json_registered_gcm_device(self):
#         with mock.patch('push_notifications.models.GCMDevice.send_message') as gcm_send_mock:
#             gcm_send_mock.side_effect = push.GCMError({"results": [{"error": "NotRegistered"}]})
#             gcm_device = GCMDeviceFactory(user=self.user)
#             push.send_to_profile(
#                 profile=self.user.profile,
#                 message='Test Message',
#                 subject='Test Subject',
#                 raise_error=False,
#             )
#             self.assertFalse(gcm_device.__class__.objects.get(pk=gcm_device.pk).active)
#
#     def test_send_to_not_registered_apns_device(self):
#         with mock.patch('push_notifications.models.APNSDevice.send_message') as apns_send_mock:
#             apns_send_mock.side_effect = push.APNSServerError(status=8)
#             apns_device = APNSDeviceFactory(user=self.user)
#             push.send_to_profile(
#                 profile=self.user.profile,
#                 message='Test Message',
#                 subject='Test Subject',
#                 raise_error=False,
#             )
#             self.assertFalse(apns_device.__class__.objects.get(pk=apns_device.pk).active)
#
#     def test_get_devices(self):
#         pusher = push.Pusher(profile=self.user.profile, message='', subject='')
#         self.assertFalse(pusher.get_devices(APNSDevice))
#         apns_device = APNSDeviceFactory(user=self.user)
#         self.assertEqual([apns_device], list(pusher.get_devices(APNSDevice)))
#         apns_device.active = False
#         apns_device.save()
#         self.assertFalse(pusher.get_devices(APNSDevice))
#         apns_device = APNSDeviceFactory(user=self.user)
#
#     def test_get_devices_with_application_id(self):
#         apns_device = APNSDeviceFactory(
#             user=self.user, application_id=settings.APNS_DEFAULT_APPLICATION_ID
#         )
#         pusher = push.Pusher(
#             profile=self.user.profile, message='', subject='', application_assignment=Event.ALL
#         )
#         self.assertEqual({apns_device}, set(pusher.get_devices(APNSDevice)))
#         gcm_device = GCMDeviceFactory(
#             user=self.user, application_id=settings.GCM_DEFAULT_APPLICATION_ID
#         )
#         pusher = push.Pusher(
#             profile=self.user.profile, message='', subject='', application_assignment=Event.ALL
#         )
#         self.assertEqual([gcm_device], list(pusher.get_devices(GCMDevice)))
#
#     def test_deactivate_all_devices(self):
#         pusher = push.Pusher(profile=self.user.profile)
#         GCMDeviceFactory(user=self.user)
#         APNSDeviceFactory(user=self.user)
#         pusher.deactivate_all_devices()
#         for klass in push.DEVICE_CLASSES:
#             self.assertFalse(pusher.get_devices(klass).count())
#
#     def test_reactivate_all_devices(self):
#         pusher = push.Pusher(profile=self.user.profile)
#         GCMDeviceFactory(user=self.user)
#         APNSDeviceFactory(user=self.user)
#         pusher.deactivate_all_devices()
#         pusher.reactivate_all_devices()
#         for klass in push.DEVICE_CLASSES:
#             self.assertEqual(pusher.get_devices(klass).count(), 1)
#
#     @mock.patch('apps.mobile_notifications.push.Pusher._send', return_value=True)
#     def test_push_notification_sent__sent_on_success(self, send_mock):
#         gcm_device = GCMDeviceFactory(user=self.user)
#
#         with assert_signal_sent(push_notification_sent) as sent_signal:
#             push.send_to_profile(profile=self.user.profile, message='msg', subject='subj')
#
#         self.assertEqual(sent_signal.call_args['event_labels'], {})
#         self.assertTrue(
#             re.match(r'^[0-9a-z-]{36}$', sent_signal.call_args['push_uuid']), "incorrect push_uuid"
#         )
#
#     @mock.patch('apps.mobile_notifications.push.Pusher._send', return_value=False)
#     def test_push_notification_sent__not_sent_on_error(self, send_mock):
#         gcm_device = GCMDeviceFactory(user=self.user)
#
#         with assert_signal_not_sent(push_notification_sent) as sent_signal:
#             push.send_to_profile(profile=self.user.profile, message='msg', subject='subj')
#
#     @mock.patch('apps.mobile_notifications.push.Pusher._send', return_value={'key': 'value'})
#     def test_pusher_send_to_all_devices__returned_list(self, send_mock):
#         gcm_device = GCMDeviceFactory(user=self.user)
#         pusher = push.Pusher(profile=self.user.profile, subject='subject', message='message')
#
#         sent_pushes = pusher.send_to_all_devices()
#         self.assertEqual(
#             [{'push_uuid': mock.ANY, 'event_labels': pusher.event_labels}], sent_pushes
#         )
