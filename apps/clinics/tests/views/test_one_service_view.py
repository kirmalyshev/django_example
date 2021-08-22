from django.forms.models import model_to_dict
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.clinics.factories import ServiceFactory, SubsidiaryFactory
from apps.clinics.models import ServiceToSubsidiary, Service
from apps.clinics.serializers import ServiceSerializer


class OneServiceViewTests(APITestCase):
    @staticmethod
    def _serialize_obj(obj: Service):
        return ServiceSerializer(instance=obj).data

    @classmethod
    def setUpTestData(cls):
        cls.service = ServiceFactory(title="test1", description="test1")
        cls.url = reverse("api.v1:service_item", args=[cls.service.id])

    def test_url(self):
        self.assertEqual(self.url, f'/api/v1/services/{self.service.id}')

    def test_get__bad_id(self):
        response = self.client.get(reverse("api.v1:service_item", args=[100500]))
        self.assertEqual(status.HTTP_404_NOT_FOUND, response.status_code)

    def test_get__no_subsidiaries(self):
        response = self.client.get(self.url)

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(self._serialize_obj(self.service), response.json())

    def test_get__with_subsidiaries(self):
        subsidiary = SubsidiaryFactory(title="test1")
        ServiceToSubsidiary.objects.create(service=self.service, subsidiary=subsidiary)
        response = self.client.get(self.url)

        self.assertEqual(status.HTTP_200_OK, response.status_code)

        expected = self._serialize_obj(self.service)
        expected["subsidiaries"] = [
            {
                "id": subsidiary.id,
                "title": subsidiary.title,
                "primary_image": None,
                'address': subsidiary.address,
                'short_address': subsidiary.short_address,
            }
        ]

        self.assertEqual(expected, response.json())
