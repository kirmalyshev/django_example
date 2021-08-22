from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.clinics.factories import (
    SubsidiaryContactFactory,
    SubsidiaryFactory,
    SubsidiaryWorkdayFactory,
)


class OneSubsidiaryViewTest(APITestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.subsidiary = SubsidiaryFactory(title="test1", description="test1")
        cls.url = reverse("api.v1:subsidiary_item", args=[cls.subsidiary.id])

    def __subsidiary_to_dict(self, subsidiary, add_images=True):
        result = {
            "id": subsidiary.id,
            "title": subsidiary.title,
            "description": subsidiary.description,
            "address": subsidiary.address,
            "short_address": subsidiary.short_address,
            "primary_image": None,
            "picture": None,
            "images": list(subsidiary.images.all()),
            "contacts": self.__contacts_to_dict_list(list(subsidiary.contacts.all())),
            "workdays": self.__workdays_to_dict_list(list(subsidiary.workdays.all())),
            "latitude": subsidiary.latitude,
            "longitude": subsidiary.longitude,
        }
        if not add_images:
            result.pop("images")
        return result

    @staticmethod
    def __contacts_to_dict_list(contacts):
        return [
            {"ordering_number": c.ordering_number, "title": c.title, "value": c.value}
            for c in contacts
        ]

    @staticmethod
    def __workdays_to_dict_list(workdays):
        return [
            {"ordering_number": w.ordering_number, "value": w.value, "weekday": w.weekday}
            for w in workdays
        ]

    def test_url(self):
        self.assertEqual(self.url, f'/api/v1/subsidiaries/{self.subsidiary.id}')

    def test_get__bad_id(self):
        response = self.client.get(reverse("api.v1:subsidiary_item", args=[100500]))
        self.assertEqual(status.HTTP_404_NOT_FOUND, response.status_code)

    def test_get__ok(self):
        response = self.client.get(self.url)

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(self.__subsidiary_to_dict(self.subsidiary), response.json())

    def test_get__with_contacts(self):
        subsidiary_contact = SubsidiaryContactFactory()
        response = self.client.get(
            reverse("api.v1:subsidiary_item", args=[subsidiary_contact.subsidiary_id])
        )

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(self.__subsidiary_to_dict(subsidiary_contact.subsidiary), response.json())

    def test_get__with_workdays(self):
        subsidiary_workday = SubsidiaryWorkdayFactory()
        response = self.client.get(
            reverse("api.v1:subsidiary_item", args=[subsidiary_workday.subsidiary.id])
        )

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(self.__subsidiary_to_dict(subsidiary_workday.subsidiary), response.json())
