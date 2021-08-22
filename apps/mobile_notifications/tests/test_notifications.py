# from django.test import TestCase
# from mock import patch, MagicMock
#
# from apps.notify.models import Event
# from apps.notify.tasks import send_event
# from apps.profiles.factories import ProfileFactory, UserFactory, PatientProfileFactory
# from ..notifications import PushBackend
# from ..serializers import ProfileSerializer
# from ...notify.constants import PUSH
# from ...notify.factories import (
#     EventFactory,
#     TypeFactory,
#     GroupFactory,
#     TemplateFactory,
#     ChannelFactory,
# )
#
#
# class UserContractorFactory(UserFactory):
#     pass
#
#
# class PushBackendTest(TestCase):
#     @classmethod
#     def setUpTestData(cls):
#         ChannelFactory(name='push', backend='PushBackend')
#
#     @patch('apps.mobile_notifications.notifications.send_to_profile')
#     def test_send(self, send_to_profile_mock):
#         backend = PushBackend(log=False)
#         customer_profile = PatientProfileFactory()
#         contractor_user = UserContractorFactory()
#
#         with patch('apps.mobile_notifications.notifications.json', MagicMock(dumps=lambda x: x)):
#             backend.send(
#                 contractor_user,
#                 event_name='order_contact_shown',
#                 message='test',
#                 subject='test',
#                 order_id=1,
#                 extra_push_payload={'key': 'value'},
#                 from_profile=customer_profile,
#             )
#
#         payload = {
#             'action': 'order_contact_shown',
#             'order_id': 1,
#             'from_user': ProfileSerializer(customer_profile).data,
#             'key': 'value',
#             'target_screen': 'default',
#         }
#
#         self.assertEqual(1, send_to_profile_mock.call_count)
#         send_to_profile_mock.assert_called_with(
#             profile=contractor_user.profile,
#             message='test',
#             payload=payload,
#             subject='test',
#             raise_error=False,
#             application_assignment=None,
#         )
#
#     @patch('apps.mobile_notifications.notifications.send_to_profile')
#     def test_send_no_extra_payload(self, send_to_profile_mock):
#         backend = PushBackend(log=False)
#         contractor_user = UserContractorFactory()
#
#         with patch('apps.mobile_notifications.notifications.json', MagicMock(dumps=lambda x: x)):
#             backend.send(
#                 contractor_user,
#                 event_name='event',
#                 message='some message',
#                 subject='some subject',
#                 thread_id='aaa-bbb',
#                 order_id=1,
#                 offer_id=2,
#             )
#
#         send_to_profile_mock.assert_called_with(
#             profile=contractor_user.profile,
#             payload={
#                 'action': 'event',
#                 'thread_id': 'aaa-bbb',
#                 'order_id': 1,
#                 'offer_id': 2,
#                 'target_screen': 'default',
#             },
#             message='some message',
#             subject='some subject',
#             raise_error=False,
#             application_assignment=None,
#         )
#
#     @patch.object(PushBackend, 'send')
#     def test_backend_integration_into_notify_app(self, send_mock):
#         customer_profile = ProfileFactory()
#         contractor_user = UserContractorFactory()
#         event_group = GroupFactory(name='Периодические уведомления')
#         event = EventFactory(
#             name='appointment_created', type=TypeFactory(name='tmp'), group=event_group
#         )
#         template = TemplateFactory(subject='Новое сообщение', channel__name=PUSH, event=event)
#         send_event(
#             'appointment_created',
#             user=contractor_user,
#             from_profile=customer_profile,
#             channel=PUSH,
#             thread_id='aaa-bbb',
#             order_id=1,
#             offer_id=2,
#         )
#         send_mock.assert_called_with(
#             user=contractor_user,
#             event_name='appointment_created',
#             thread_id='aaa-bbb',
#             from_profile=customer_profile,
#             order_id=1,
#             offer_id=2,
#             channel=PUSH,
#             event_id=event.id,
#             message=template.message,
#             subject='Новое сообщение',
#             push_application_assignment=Event.ALL,
#         )
