from django.test import TestCase

from apps.clinics.factories import ServiceFactory
from apps.clinics.models import Service


class ServiceTest(TestCase):
    def test_mark_hidden(self):
        service: Service = ServiceFactory(is_displayed=True)
        self.assertTrue(service.is_displayed)
        service.mark_hidden()
        updated_doctor = Service.objects.get(id=service.id)
        self.assertFalse(updated_doctor.is_displayed)

    def test_mark_displayed(self):
        doctor: Service = ServiceFactory(is_displayed=False)
        self.assertFalse(doctor.is_displayed)
        doctor.mark_displayed()
        updated_doctor = Service.objects.get(id=doctor.id)
        self.assertTrue(updated_doctor.is_displayed)
