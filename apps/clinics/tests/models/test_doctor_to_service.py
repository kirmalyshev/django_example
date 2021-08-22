from django.db import IntegrityError
from django.test import TestCase

from apps.clinics.factories import DoctorFactory, ServiceFactory
from apps.clinics.models import DoctorToService


class DoctorToServiceTest(TestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.doctor = DoctorFactory()
        cls.service = ServiceFactory()

    def test_save__ok(self):
        DoctorToService.objects.create(doctor=self.doctor, service=self.service)
        self.assertEqual(list(self.doctor.services.all()), [self.service])
        self.assertEqual(list(self.service.doctor_set.all()), [self.doctor])

    def test_save__raises(self):
        DoctorToService.objects.create(doctor=self.doctor, service=self.service)
        with self.assertRaises(IntegrityError):
            DoctorToService.objects.create(doctor=self.doctor, service=self.service)
        self.assertEqual(list(self.doctor.services.all()), [self.service])
        self.assertEqual(list(self.service.doctor_set.all()), [self.doctor])
