from django.db import IntegrityError
from django.test import TestCase

from apps.clinics.factories import ServiceFactory, SubsidiaryFactory
from apps.clinics.models import ServiceToSubsidiary


class ServiceToSubsidiaryTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.service = ServiceFactory()
        cls.subsidiary = SubsidiaryFactory()

    def test_save__ok(self):
        ServiceToSubsidiary.objects.create(service=self.service, subsidiary=self.subsidiary)
        self.assertEqual(list(self.service.subsidiaries.all()), [self.subsidiary])
        self.assertEqual(list(self.subsidiary.service_set.all()), [self.service])

    def test_save__raises(self):
        ServiceToSubsidiary.objects.create(service=self.service, subsidiary=self.subsidiary)
        with self.assertRaises(IntegrityError):
            ServiceToSubsidiary.objects.create(service=self.service, subsidiary=self.subsidiary)
        self.assertEqual(list(self.service.subsidiaries.all()), [self.subsidiary])
        self.assertEqual(list(self.subsidiary.service_set.all()), [self.service])
