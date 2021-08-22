from typing import List

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.clinics.factories import DoctorFactory, ServiceFactory, SubsidiaryFactory
from apps.clinics.models import DoctorToService, DoctorToSubsidiary, Service, Doctor


class DoctorListViewTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.doctor: Doctor = DoctorFactory(description="test1", is_fake=False)
        cls.url = reverse("api.v1:doctor_list")

    def __doctor_to_dict(self, doctor):
        return {
            'id': doctor.id,
            'full_name': doctor.profile.full_name,
            'picture': None,
            'description': doctor.description,
            'experience': doctor.experience,
            'education': doctor.education,
            'speciality_text': doctor.speciality_text,
            'services': self.__services_to_dict_list(doctor.services.all()),
            'subsidiaries': self.__subsidiaries_to_dict_list(list(doctor.subsidiaries.all())),
            'is_timeslots_available_for_patient': doctor.is_timeslots_available_for_patient,
            "grade": None,
        }

    @staticmethod
    def __subsidiaries_to_dict_list(services):
        return [{"id": s.id, "title": s.title} for s in services]

    @staticmethod
    def __services_to_dict_list(services: List[Service]):
        return [
            {
                "id": s.id,
                "title": s.title,
                'level': s.level,
                # 'prices': list(s.prices.all()),
                "is_visible_for_appointments": s.is_visible_for_appointments,
            }
            for s in services
        ]

    def test_url(self):
        self.assertEqual(self.url, '/api/v1/doctors')

    def test_get__ok(self):
        response = self.client.get(self.url)

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual([self.__doctor_to_dict(self.doctor)], response.json()['results'])

    def test_get__only_visible_to_patient(self):
        removed = DoctorFactory(is_removed=True, is_displayed=True)
        hidden = DoctorFactory(is_removed=False, is_displayed=False)
        removed_and_hidden = DoctorFactory(is_removed=True, is_displayed=False)
        response = self.client.get(self.url)

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        data = response.json()['results']
        id_values = {item['id'] for item in data}
        self.assertNotIn(removed.id, id_values)
        self.assertNotIn(hidden.id, id_values)
        self.assertNotIn(removed_and_hidden.id, id_values)
        self.assertEqual([self.__doctor_to_dict(self.doctor)], data)

    def test_get__with_services(self):
        service = ServiceFactory()
        DoctorToService.objects.create(service=service, doctor=self.doctor)
        response = self.client.get(self.url)

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual([self.__doctor_to_dict(self.doctor)], response.json()['results'])

    def test_get__with_subsidiaries(self):
        subsidiary = SubsidiaryFactory()
        DoctorToSubsidiary.objects.create(subsidiary=subsidiary, doctor=self.doctor)
        response = self.client.get(self.url)

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual([self.__doctor_to_dict(self.doctor)], response.json()['results'])

    def test_get__filter_by_subsidiary_ids(self):
        subsidiary_1 = SubsidiaryFactory(title='test1')
        DoctorToSubsidiary.objects.create(subsidiary=subsidiary_1, doctor=self.doctor)
        doctor_2 = DoctorFactory(description='test2')
        subsidiary_2 = SubsidiaryFactory(title='test2')
        DoctorToSubsidiary.objects.create(subsidiary=subsidiary_2, doctor=doctor_2)
        response = self.client.get(self.url, {'subsidiary_ids': [subsidiary_2.id]})

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual([self.__doctor_to_dict(doctor_2)], response.json()['results'])

    def test_get__filter_by_service_ids(self):
        service_1 = ServiceFactory(title='test1')
        DoctorToService.objects.create(service=service_1, doctor=self.doctor)
        doctor_2 = DoctorFactory(description='test2')
        service_2 = ServiceFactory(title='test2')
        DoctorToService.objects.create(service=service_2, doctor=doctor_2)
        response = self.client.get(self.url, {'service_ids': [service_2.id]})

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual([self.__doctor_to_dict(doctor_2)], response.json()['results'])

    def test_get__filter_by_service_ids_and_subsidiary_ids(self):
        service_1 = ServiceFactory(title='test1')
        subsidiary_1 = SubsidiaryFactory(title='test1')
        DoctorToSubsidiary.objects.create(subsidiary=subsidiary_1, doctor=self.doctor)
        DoctorToService.objects.create(service=service_1, doctor=self.doctor)
        doctor_2 = DoctorFactory(description='test2')
        service_2 = ServiceFactory(title='test2')
        subsidiary_2 = SubsidiaryFactory(title='test2')
        DoctorToSubsidiary.objects.create(subsidiary=subsidiary_2, doctor=doctor_2)
        DoctorToService.objects.create(service=service_2, doctor=doctor_2)
        response = self.client.get(
            self.url, {'service_ids': [service_2.id], 'subsidiary_ids': [subsidiary_2.id]}
        )

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual([self.__doctor_to_dict(doctor_2)], response.json()['results'])

    def test_get__filter_bad_keyword(self):
        response = self.client.get(self.url, {'services_ids': [123], 'subsidiaries_ids': [456]})

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual([self.__doctor_to_dict(self.doctor)], response.json()['results'])

    def test_get__filter_bad_service_ids(self):
        response = self.client.get(self.url, {'service_ids': 'HELLOWORLD'})

        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

    def test_get__filter_bad_subsidiary_ids(self):
        response = self.client.get(self.url, {'subsidiary_ids': 'HELLOWORLD'})

        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

    def test_get__filter_by_without_fakes(self):
        doctor_2: Doctor = DoctorFactory(description='test2', is_fake=True)
        self.assertTrue(doctor_2.is_fake)
        response = self.client.get(self.url, {'without_fakes': 1})

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        results = response.json()['results']
        actual_result_ids = [x['id'] for x in results]
        self.assertEqual([self.doctor.id], actual_result_ids)
        self.assertEqual([self.__doctor_to_dict(self.doctor)], results)
