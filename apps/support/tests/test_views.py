from django.core.cache import cache
from django.test import override_settings
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from apps.clinics.factories import PatientUserFactory, PatientFactory
from apps.support.models import SupportRequest
from apps.tools.apply_tests.utils import assert_sends_mail


@override_settings(
    REST_FRAMEWORK={'DEFAULT_THROTTLE_RATES': {"create_support_request": "100500/sec"}}
)
class SupportRequestViewTest(APITestCase):
    maxDiff = None
    url = reverse("api.v1:support:create_request")

    def setUp(self):
        cache.clear()

    def test_url(self):
        self.assertEqual('/api/v1/support/create_request', self.url)

    def test_get__not_allowed(self):
        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_405_METHOD_NOT_ALLOWED, response.status_code)

    def test_post__bad_email(self):
        response = self.client.post(self.url, data={'email': 'im so bad', 'text': 'blabla'})
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        data = response.json()
        self.assertEqual({'email': ['Введите корректный адрес электронной почты.']}, data, data)

    def test_post__no_email(self):
        response = self.client.post(self.url, data={'email': '', 'text': 'blabla'})
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        data = response.json()
        self.assertEqual({'email': ['Это поле не может быть пустым.']}, data, data)

    def test_post__no_text(self):
        response = self.client.post(self.url, data={'email': 'anon@test.com', 'text': ''})
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        data = response.json()
        self.assertEqual({'text': ['Это поле не может быть пустым.']}, data, data)

    def test_post__anonymous__support_request_created(self):
        with assert_sends_mail(
            subject='Обращение в саппорт', body='Email: anon@test.com\nТелефон: None\n\n im hungry',
        ):
            response = self.client.post(
                self.url, data={'email': 'anon@test.com', 'text': 'im hungry'}
            )
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        data = response.json()
        latest_request = SupportRequest.objects.latest('id')
        self.assertEqual(
            {'id': latest_request.id, 'email': 'anon@test.com', 'text': 'im hungry', 'phone': None},
            data,
            data,
        )
        self.assertEqual('anon@test.com', latest_request.email)
        self.assertEqual('im hungry', latest_request.text)
        self.assertIsNone(latest_request.phone)
        self.assertIsNone(latest_request.user)

    def test_post__patient__support_request_created(self):
        user = PatientUserFactory(patient=PatientFactory())
        self.client.force_authenticate(user)
        with assert_sends_mail(
            subject='Обращение в саппорт',
            body='Email: patient@test.com\nТелефон: None\n\n im angry',
        ):
            response = self.client.post(
                self.url, data={'email': 'patient@test.com', 'text': 'im angry'}
            )
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        data = response.json()
        latest_request = SupportRequest.objects.latest('id')
        self.assertEqual(
            {
                'id': latest_request.id,
                'email': 'patient@test.com',
                'text': 'im angry',
                'phone': None,
            },
            data,
            data,
        )
        self.assertEqual('patient@test.com', latest_request.email)
        self.assertEqual('im angry', latest_request.text)
        self.assertIsNone(latest_request.phone)
        self.assertEqual(user, latest_request.user)
