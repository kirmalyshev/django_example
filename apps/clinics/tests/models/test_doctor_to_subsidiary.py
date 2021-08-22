from django.db import IntegrityError
from django.test import TestCase

from apps.clinics.factories import DoctorFactory, SubsidiaryFactory
from apps.clinics.models import DoctorToSubsidiary


class DoctorToSubsidiaryTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.doctor = DoctorFactory()
        cls.subsidiary = SubsidiaryFactory()

    def test_save__ok(self):
        DoctorToSubsidiary.objects.create(doctor=self.doctor, subsidiary=self.subsidiary)
        self.assertEqual(list(self.doctor.subsidiaries.all()), [self.subsidiary])
        self.assertEqual(list(self.subsidiary.doctor_set.all()), [self.doctor])

    def test_save__raises(self):
        DoctorToSubsidiary.objects.create(doctor=self.doctor, subsidiary=self.subsidiary)
        with self.assertRaises(IntegrityError):
            DoctorToSubsidiary.objects.create(doctor=self.doctor, subsidiary=self.subsidiary)
        self.assertEqual(list(self.doctor.subsidiaries.all()), [self.subsidiary])
        self.assertEqual(list(self.subsidiary.doctor_set.all()), [self.doctor])
