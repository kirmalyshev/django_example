import mock
from django.test import TestCase

from apps.appointments.constants import (
    AppointmentStatus,
    RELATED_PATIENT_FULL_NAME,
    DOCTOR_ID,
    ADDITIONAL_NOTES,
    IS_FOR_WHOLE_DAY,
    HUMAN_START,
    DOCTOR,
    END,
    HUMAN_WEEKDAY,
    HUMAN_START_TIME,
    PATIENT_ID,
    HUMAN_START_DATE_SHORT,
    HUMAN_START_DATE,
    START,
    SUBSIDIARY,
    SERVICE,
    HUMAN_START_DATETIME,
)
from apps.appointments.factories import AppointmentFactory
from apps.appointments.serializers import AppointmentListSerializer
from apps.clinics.factories import DoctorFactory, SubsidiaryFactory, ServiceFactory
from apps.reviews.constants import GRADE


class AppointmentListSerializerTest(TestCase):
    maxDiff = None
    serializer_class = AppointmentListSerializer

    def setUp(self) -> None:
        self.subsidiary = SubsidiaryFactory()
        self.doctor = DoctorFactory(
            description='desc AppointmentListSerializerTest',
            speciality_text='experience AppointmentListSerializerTest',
        )
        self.service = ServiceFactory()
        self.appointment = AppointmentFactory(
            doctor=self.doctor,
            subsidiary=self.subsidiary,
            service=self.service,
            status=AppointmentStatus.PLANNED,
        )

    def test_valid_data__appointment_serializer(self):
        serializer = self.serializer_class(instance=self.appointment)
        actual_data = serializer.data

        expected_doctor = {
            'id': self.doctor.id,
            'full_name': self.doctor.profile.full_name,
            'description': 'desc AppointmentListSerializerTest',
            'speciality_text': 'experience AppointmentListSerializerTest',
            'picture': None,
            'is_timeslots_available_for_patient': False,
        }
        expected_subsidiary = {
            'id': self.subsidiary.id,
            'title': self.subsidiary.title,
            'address': self.subsidiary.address,
            'short_address': self.subsidiary.short_address,
            'latitude': self.subsidiary.latitude,
            'longitude': self.subsidiary.longitude,
        }
        expected_service = {'id': self.service.id, 'title': self.service.title}
        expected_data = {
            'id': self.appointment.id,
            START: mock.ANY,
            HUMAN_START: self.appointment.human_start_tz,
            HUMAN_START_DATE: self.appointment.human_start_date,
            HUMAN_START_DATETIME: self.appointment.human_start_datetime,
            HUMAN_START_DATE_SHORT: self.appointment.start_date_tz_formatted__short,
            HUMAN_WEEKDAY: self.appointment.human_weekday,
            HUMAN_START_TIME: self.appointment.human_start_time,
            END: mock.ANY,
            PATIENT_ID: self.appointment.patient_id,
            DOCTOR: expected_doctor,
            DOCTOR_ID: expected_doctor["id"],
            SUBSIDIARY: expected_subsidiary,
            SERVICE: expected_service,
            'status': {
                'code': self.appointment.status,
                'value': self.appointment.get_status_display(),
            },
            'reason_text': self.appointment.reason_text,
            'is_payment_enabled': False,
            'is_cancel_by_patient_available': True,
            'is_archived': False,
            'is_finished': False,
            'price': None,
            'has_timeslots': False,
            GRADE: None,
            RELATED_PATIENT_FULL_NAME: "",
            IS_FOR_WHOLE_DAY: False,
        }
        actual_keys = actual_data.keys()
        self.assertEqual(expected_data.keys(), actual_keys, actual_keys)
        self.assertEqual(expected_service, actual_data['service'])
        self.assertEqual(expected_doctor, actual_data['doctor'], actual_data['doctor'])
        self.assertEqual(expected_subsidiary, actual_data['subsidiary'], actual_data['subsidiary'])
        self.assertEqual(expected_data, actual_data, actual_data)
