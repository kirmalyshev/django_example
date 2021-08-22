from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.clinics.factories import (
    SubsidiaryContactFactory,
    SubsidiaryFactory,
    SubsidiaryWorkdayFactory,
)


class SubsidiaryListViewTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('api.v1:subsidiary_list')
        cls.subsidiary = SubsidiaryFactory(title='test1', description='test1')

    def __subsidiary_to_dict(self, subsidiary, add_images=True):
        result = {
            "id": subsidiary.id,
            "title": subsidiary.title,
            "description": subsidiary.description,
            "address": subsidiary.address,
            "short_address": subsidiary.short_address,
            "primary_image": None,
            "picture": None,
            "contacts": self.__contacts_to_dict_list(list(subsidiary.contacts.all())),
            "workdays": self.__workdays_to_dict_list(list(subsidiary.workdays.all())),
            "latitude": subsidiary.latitude,
            "longitude": subsidiary.longitude,
        }

        if add_images:
            result["images"] = list(subsidiary.images.all())
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
        self.assertEqual(self.url, '/api/v1/subsidiaries')

    def test_get__ok(self):
        response = self.client.get(self.url)

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(
            [self.__subsidiary_to_dict(self.subsidiary, add_images=False)],
            response.json()['results'],
        )

    def test_get__with_contacts(self):
        subsidiary_contact = SubsidiaryContactFactory()
        response = self.client.get(self.url)

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(
            [
                self.__subsidiary_to_dict(x, add_images=False)
                for x in (self.subsidiary, subsidiary_contact.subsidiary)
            ],
            response.json()['results'],
        )

    def test_get__with_workdays(self):
        subsidiary_workday = SubsidiaryWorkdayFactory()
        response = self.client.get(self.url)

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(
            [
                self.__subsidiary_to_dict(x, add_images=False)
                for x in (self.subsidiary, subsidiary_workday.subsidiary)
            ],
            response.json()['results'],
        )

    def test_get__only_visible_to_patient(self):
        removed = SubsidiaryFactory(is_removed=True, is_displayed=True)
        hidden = SubsidiaryFactory(is_removed=False, is_displayed=False)
        removed_and_hidden = SubsidiaryFactory(is_removed=True, is_displayed=False)
        response = self.client.get(self.url)

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        data = response.json()['results']
        id_values = {item['id'] for item in data}
        self.assertNotIn(removed.id, id_values)
        self.assertNotIn(hidden.id, id_values)
        self.assertNotIn(removed_and_hidden.id, id_values)
        self.assertEqual([self.__subsidiary_to_dict(self.subsidiary, add_images=False)], data)
