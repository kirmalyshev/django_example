from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.clinics.factories import DoctorFactory, ServiceFactory, SubsidiaryFactory
from apps.clinics.models import DoctorToService, DoctorToSubsidiary


class OneDoctorViewTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.doctor = DoctorFactory(description='test1')
        cls.url = reverse("api.v1:doctor_item", args=[cls.doctor.id])

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
            'subsidiaries': self.__services_or_subsidiaries_to_dict_list(
                list(doctor.subsidiaries.all())
            ),
            'is_timeslots_available_for_patient': doctor.is_timeslots_available_for_patient,
            "grade": None,
            "youtube_video_id": doctor.youtube_video_id,
        }

    @staticmethod
    def __services_or_subsidiaries_to_dict_list(services):
        return [{"id": s.id, "title": s.title} for s in services]

    @staticmethod
    def __services_to_dict_list(services):
        return [
            {
                "id": s.id,
                "title": s.title,
                'level': s.level,
                'prices': list(s.prices.all()),
                "is_visible_for_appointments": s.is_visible_for_appointments,
            }
            for s in services
        ]

    def test_url(self):
        self.assertEqual(self.url, f'/api/v1/doctors/{self.doctor.id}')

    def test_get__bad_id(self):
        response = self.client.get(reverse("api.v1:doctor_item", args=[100500]))
        self.assertEqual(status.HTTP_404_NOT_FOUND, response.status_code)

    def test_get__ok(self):
        response = self.client.get(self.url)

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(self.__doctor_to_dict(self.doctor), response.json())

    def test_get__with_services(self):
        service = ServiceFactory()
        DoctorToService.objects.create(service=service, doctor=self.doctor)
        response = self.client.get(self.url)

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(self.__doctor_to_dict(self.doctor), response.json())

    def test_get__with_subsidiaries(self):
        subsidiary = SubsidiaryFactory()
        DoctorToSubsidiary.objects.create(subsidiary=subsidiary, doctor=self.doctor)
        response = self.client.get(self.url)

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(self.__doctor_to_dict(self.doctor), response.json())
