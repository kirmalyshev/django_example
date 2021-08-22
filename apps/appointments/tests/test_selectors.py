from django.test import TestCase

from apps.appointments.factories import AppointmentFactory
from apps.appointments.selectors import AllAppointmentsSelector


class AllAppointmentsSelectorTest(TestCase):
    def test_get_or_none__none_returned(self):
        actual = AllAppointmentsSelector.get_or_none(100500)
        self.assertIsNone(actual)

    def test_get_or_none__obj_returned(self):
        appointment = AppointmentFactory()
        actual = AllAppointmentsSelector.get_or_none(appointment.id)
        self.assertEqual(actual, appointment)
