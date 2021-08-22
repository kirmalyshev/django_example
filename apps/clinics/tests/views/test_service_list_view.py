from typing import Dict

from django.urls import reverse
from rest_framework import status

from apps.clinics.constants import MobileAppSections
from apps.clinics.factories import ServiceFactory, SubsidiaryFactory, DoctorFactory
from apps.clinics.models import ServiceToSubsidiary, Service
from apps.clinics.serializers import ServicePriceSerializer, SubsidiaryForServiceSerializer
from apps.tools.apply_tests.case import TestCaseCheckStatusCode


class ServiceListViewTest(TestCaseCheckStatusCode):
    maxDiff = None
    url = reverse('api.v1:service_list')

    @classmethod
    def setUpTestData(cls):
        cls.root_service = ServiceFactory(
            title='Однажды в студеную зимнюю пору',
            description='я из лесу вышел - был сильный мороз',
            is_displayed=True,
            is_visible_for_appointments=False,
        )

    def test_url(self):
        self.assertEqual(self.url, '/api/v1/services')

    def _serialize_service(self, obj: Service) -> Dict:
        return {
            'id': obj.id,
            'title': obj.title,
            'description': obj.description,
            'level': obj.level,
            'parent_id': obj.parent_id,
            'children_count': obj.get_children().displayed().count(),
            'priority': obj.priority,
            'subsidiaries': SubsidiaryForServiceSerializer(
                instance=obj.subsidiaries.all(), many=True
            ).data,
            'prices': ServicePriceSerializer(instance=obj.prices.all(), many=True).data,
            'is_visible_for_appointments': obj.is_visible_for_appointments,
        }

    def test_get__only_visible_to_patient(self):
        hidden = ServiceFactory(is_displayed=False)
        response = self.client.get(self.url)

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        data = response.json()['results']
        id_values = {item['id'] for item in data}
        self.assertNotIn(hidden.id, id_values)
        self.assertEqual(
            [self._serialize_service(self.root_service)], data,
        )

    def test_get__no_subsidiaries(self):
        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        response_data = response.json()['results']
        self.assertEqual(
            [self._serialize_service(self.root_service)], response_data,
        )

    def test_get__with_subsidiaries(self):
        subsidiary = SubsidiaryFactory(title='Гляжу - поднимается медленно в гору')
        ServiceToSubsidiary.objects.create(service=self.root_service, subsidiary=subsidiary)
        response = self.client.get(self.url)

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(
            [self._serialize_service(self.root_service)], response.json()['results'],
        )

    def test_get__filter_by_subsidiary_ids(self):
        subsidiary_1 = SubsidiaryFactory(title='откуда дровишки?')
        ServiceToSubsidiary.objects.create(service=self.root_service, subsidiary=subsidiary_1)
        service_2 = ServiceFactory(
            title='Шаганэ ты моя, Шаганэ', description='оттого что я с севера, что ли'
        )
        subsidiary_2 = SubsidiaryFactory(title='я хочу показать тебе поле')
        ServiceToSubsidiary.objects.create(service=service_2, subsidiary=subsidiary_2)

        response = self.client.get(self.url, {'subsidiary_ids': [subsidiary_2.id]})
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(
            [self._serialize_service(service_2)], response.json()['results'],
        )

    def test_get__filter_bad_subsidiary_ids(self):
        subsidiary_1 = SubsidiaryFactory(title='откуда дровишки?')
        ServiceToSubsidiary.objects.create(service=self.root_service, subsidiary=subsidiary_1)

        response = self.client.get(self.url, {'subsidiary_ids': 'HELLOWORLD'})
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

    def test_get__filter_by_only_root__true(self):
        child = ServiceFactory(title='child', parent=self.root_service)
        response = self.client.get(self.url, {'only_root': True})
        self.check_status_code(response, status.HTTP_200_OK)

        actual_data = response.json()['results']
        expected_data = [self._serialize_service(self.root_service)]
        self.assertEqual(expected_data, actual_data, actual_data)

    def test_get__filter_by_only_root__false(self):
        child = ServiceFactory(title='child', description='child_desc', parent=self.root_service)

        response = self.client.get(self.url, {'only_root': False})
        self.check_status_code(response, status.HTTP_200_OK)

        actual_data = response.json()['results']
        expected_data = [
            self._serialize_service(self.root_service),
            self._serialize_service(child),
        ]
        # self.assertEqual(expected_data, actual_data, actual_data)
        self.assertEqual(
            {i['id'] for i in expected_data}, {i['id'] for i in actual_data},
        )

    def test__filter_by__parent_id__ok(self):
        child = ServiceFactory(title='child', parent=self.root_service)
        response = self.client.get(self.url, {'parent_id': self.root_service.id})
        self.check_status_code(response, status.HTTP_200_OK)

        actual_data = response.json()['results']
        expected_data = [self._serialize_service(child)]
        self.assertEqual(expected_data, actual_data, actual_data)

    def test__filter_by__parent_id__bad(self):
        response = self.client.get(self.url, {'parent_id': 100500})
        self.check_status_code(response, status.HTTP_200_OK)

        actual_data = response.json()['results']
        expected_data = []
        self.assertEqual(expected_data, actual_data, actual_data)

    def test__filter_by__mobile_app_section__bad_value(self):
        response = self.client.get(self.url, {'mobile_app_section': 'ololol'})
        self.check_status_code(response, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertEqual(
            {
                'api_errors': [
                    {
                        'code': 'validation_error',
                        'source': {'parameter': 'mobile_app_section'},
                        'title': 'Invalid mobile_app_section value. Available values: '
                        "('services', 'doctors', 'create_appointment_by_patient')",
                    }
                ],
                'mobile_app_section': [
                    'Invalid mobile_app_section value. Available values: '
                    "('services', 'doctors', 'create_appointment_by_patient')"
                ],
            },
            data,
            data,
        )

    def test__filter_by__mobile_app_section__no_value(self):
        visible = ServiceFactory(title='visible', is_visible_for_appointments=True)
        only_displayed = self.root_service
        non_visible = ServiceFactory(
            title='non_visible', is_visible_for_appointments=False, is_displayed=False
        )

        response = self.client.get(self.url, {'mobile_app_section': ''})
        self.check_status_code(response, status.HTTP_200_OK)
        actual_data = response.json()['results']
        self.assertEqual(2, len(actual_data))
        expected_data = [self._serialize_service(only_displayed), self._serialize_service(visible)]
        self.assertEqual(
            {i['id'] for i in expected_data}, {i['id'] for i in actual_data},
        )
        # self.assertEqual(expected_data, actual_data, actual_data)

    def test__filter_by__mobile_app_section__doctors(self):
        """
        here must be only visible services with doctors
        """
        visible = ServiceFactory(
            title='visible', is_visible_for_appointments=True, is_displayed=True
        )
        only_displayed = self.root_service
        non_visible = ServiceFactory(
            title='non_visible', is_visible_for_appointments=False, is_displayed=False
        )
        visible_with_doctor = ServiceFactory(
            title='with_doctor', is_visible_for_appointments=True, is_displayed=True
        )
        doctor = DoctorFactory(services=[visible_with_doctor])

        response = self.client.get(self.url, {'mobile_app_section': MobileAppSections.DOCTORS})
        self.check_status_code(response, status.HTTP_200_OK)
        actual_data = response.json()['results']
        self.assertEqual(1, len(actual_data))
        expected_data = [self._serialize_service(visible_with_doctor)]
        self.assertEqual(expected_data, actual_data, actual_data)

    def test__filter_by__mobile_app_section__services(self):
        visible = ServiceFactory(title='visible', is_visible_for_appointments=True)
        only_displayed = self.root_service
        non_visible = ServiceFactory(
            title='non_visible', is_visible_for_appointments=False, is_displayed=False
        )

        response = self.client.get(self.url, {'mobile_app_section': MobileAppSections.SERVICES})
        self.check_status_code(response, status.HTTP_200_OK)
        actual_data = response.json()['results']
        self.assertEqual(2, len(actual_data))
        expected_data = [self._serialize_service(only_displayed), self._serialize_service(visible)]
        self.assertEqual(
            {i['id'] for i in expected_data}, {i['id'] for i in actual_data},
        )
        # self.assertEqual(expected_data, actual_data, actual_data)

    def test__filter_by__mobile_app_section__create_appointment_by_patient(self):
        """
        here must be only visible services with visible doctors
        """
        visible = ServiceFactory(
            title='visible', is_visible_for_appointments=True, is_displayed=True
        )
        only_displayed = self.root_service
        non_visible = ServiceFactory(
            title='non_visible', is_visible_for_appointments=False, is_displayed=False
        )
        visible_with_doctor = ServiceFactory(
            title='with_doctor', is_visible_for_appointments=True, is_displayed=True
        )
        visible_with_fake_doctor = ServiceFactory(
            title='with_fake_doctor', is_visible_for_appointments=True, is_displayed=True
        )
        doctor = DoctorFactory(services=[visible_with_doctor])
        fake_doctor = DoctorFactory(services=[visible_with_fake_doctor], is_fake=True)

        response = self.client.get(
            self.url, {'mobile_app_section': MobileAppSections.CREATE_APPOINTMENT_BY_PATIENT}
        )
        self.check_status_code(response, status.HTTP_200_OK)
        actual_data = response.json()['results']
        self.assertEqual(1, len(actual_data))
        expected_data = [self._serialize_service(visible_with_doctor)]
        self.assertEqual(expected_data, actual_data, actual_data)
