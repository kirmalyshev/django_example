from django.test import TestCase

from apps.appointments.constants import AppointmentStatus, APPOINTMENT_ID
from apps.appointments.factories import AppointmentFactory
from apps.clinics.factories import PatientFactory
from apps.profiles.models import Relation
from apps.reviews.constants import GRADE
from apps.reviews.workflow import ReviewWorkflow
from rest_framework.exceptions import ValidationError as DRFValidationError, ErrorDetail


class ReviewWorkflowTest(TestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.patient = PatientFactory()

    def setUp(self) -> None:
        self.appointment = AppointmentFactory(
            patient=self.patient, status=AppointmentStatus.PLANNED
        )

    def test_create_ok__for_own_appointment(self):
        new_review = ReviewWorkflow.create_by_patient(
            patient=self.patient,
            data={
                APPOINTMENT_ID: self.appointment.id,
                GRADE: 3,
                'text': 'test_create_ok__for_own_appointment',
            },
        )
        self.assertEqual(new_review.author_patient, self.patient)
        self.assertEqual(new_review.appointment.id, self.appointment.id)
        self.assertEqual(new_review.text, "test_create_ok__for_own_appointment")

    def test_create_ok__for_related_appointment(self):
        child_patient = PatientFactory()
        relation: Relation = Relation.objects.create(
            master=self.patient.profile,
            slave=child_patient.profile,
            can_update_slave_appointments=True,
        )
        related_appointment = AppointmentFactory(patient=child_patient)

        new_review = ReviewWorkflow.create_by_patient(
            patient=self.patient,
            data={APPOINTMENT_ID: related_appointment.id, GRADE: 2, 'text': 'щтощ'},
        )
        self.assertEqual(new_review.author_patient, self.patient)
        self.assertEqual(new_review.appointment, related_appointment)

    def test_create_fail__for_non_related_appointment(self):
        other_patient = PatientFactory()
        other_appointment = AppointmentFactory(patient=other_patient)

        with self.assertRaises(DRFValidationError) as err_context:
            new_review = ReviewWorkflow.create_by_patient(
                patient=self.patient,
                data={APPOINTMENT_ID: other_appointment.id, GRADE: 2, 'text': 'щтощ'},
            )
        self.assertEqual(
            [ErrorDetail(string='No appointment found for passed appointment_id', code='invalid',)],
            err_context.exception.detail,
            err_context.exception.detail,
        )
