from django.test import TestCase

from apps.clinics.factories import DoctorFactory
from apps.clinics.models import Doctor


class DoctorTest(TestCase):
    def test_mark_hidden(self):
        doctor: Doctor = DoctorFactory(is_displayed=True)
        self.assertTrue(doctor.is_displayed)
        doctor.mark_hidden()
        updated_doctor = Doctor.objects.get(id=doctor.id)
        self.assertFalse(updated_doctor.is_displayed)

    def test_mark_displayed(self):
        doctor: Doctor = DoctorFactory(is_displayed=False)
        self.assertFalse(doctor.is_displayed)
        doctor.mark_displayed()
        updated_doctor = Doctor.objects.get(id=doctor.id)
        self.assertTrue(updated_doctor.is_displayed)

    def test_delete__marked_hidden(self):
        doctor: Doctor = DoctorFactory(is_displayed=True, is_removed=False)
        self.assertTrue(doctor.is_displayed)
        doctor.delete()
        updated_doctor = Doctor.all_objects.get(id=doctor.id)
        self.assertFalse(updated_doctor.is_displayed)
        self.assertTrue(updated_doctor.is_removed)
