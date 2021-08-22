from datetime import timedelta, datetime

from django.urls import reverse
from django.utils import timezone
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase

from apps.appointments.constants import (
    APPOINTMENT_DATETIME_FORMAT,
    AppointmentStatus,
    ONLY_FUTURE,
    ONLY_PAST,
    RELATED_PATIENT_FULL_NAME,
    IS_FOR_WHOLE_DAY,
    ADDITIONAL_NOTES,
    DOCTOR,
    SUBSIDIARY,
    SERVICE,
    HUMAN_START,
    START,
    HUMAN_START_DATE,
    HUMAN_START_DATE_SHORT,
    HUMAN_WEEKDAY,
    HUMAN_START_TIME,
    DOCTOR_ID,
    PATIENT_ID,
    END,
    PATIENT_FULL_NAME,
    SERVICE_ID,
    REASON_TEXT,
    PRICE,
    TARGET_PATIENT,
    TARGET_PATIENT_ID,
    TIME_SLOT_ID,
    AppointmentCreatedValues,
    HUMAN_START_DATETIME,
)
from apps.appointments.factories import (
    AppointmentFactory,
    TimeSlotFactory,
)
from apps.appointments.models import Appointment, TimeSlot
from apps.appointments.serializers import (
    TimeSlotSerializer,
    AppointmentListSerializer,
)
from apps.clinics.factories import (
    PatientUserFactory,
    SubsidiaryFactory,
    DoctorFactory,
    ServiceFactory,
    PatientFactory,
)
from apps.clinics.models import Doctor, Patient
from apps.clinics.test_tools import add_child_relation
from apps.core.utils import now_in_default_tz
from apps.profiles.factories import UserFactory, DoctorProfileFactory
from apps.profiles.models import Relation
from apps.reviews.constants import GRADE
from apps.tools.apply_tests.case import TestCaseCheckStatusCode


class AppointmentListViewTest(TestCaseCheckStatusCode):
    maxDiff = None

    url = reverse('api.v1:appointments:list')

    @classmethod
    def setUpTestData(cls):
        cls.patient_user = PatientUserFactory()
        cls.patient = cls.patient_user.patient
        cls.appointment = AppointmentFactory(patient=cls.patient, status=AppointmentStatus.PLANNED)
        cls.EXPECTED_APPOINTMENT_LIST_KEYS = {
            'id',
            START,
            HUMAN_START,
            HUMAN_START_DATE,
            HUMAN_START_DATETIME,
            HUMAN_START_DATE_SHORT,
            HUMAN_WEEKDAY,
            HUMAN_START_TIME,
            END,
            PATIENT_ID,
            DOCTOR_ID,
            DOCTOR,
            SUBSIDIARY,
            SERVICE,
            'status',
            REASON_TEXT,
            'is_payment_enabled',
            'is_cancel_by_patient_available',
            'is_archived',
            'is_finished',
            PRICE,
            'has_timeslots',
            GRADE,
            RELATED_PATIENT_FULL_NAME,
            IS_FOR_WHOLE_DAY,
        }

    def test_access__anonymous(self):
        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_401_UNAUTHORIZED, response.status_code)

    def test_access__patient(self):
        self.assertTrue(self.patient_user.is_patient)
        self.client.force_login(self.patient_user)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)

    def test_access__not_patient(self):
        user = UserFactory(profile=DoctorProfileFactory())
        self.assertTrue(user.is_doctor)
        self.client.force_login(user)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_data__no_appointments(self):
        user = PatientUserFactory()
        patient = user.profile.patient
        self.assertFalse(Appointment.objects.filter(patient=patient).exists())

        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertEqual([], response.json()['results'])

    def test_data__for_current_patient(self):
        user_2 = PatientUserFactory()
        patient_2 = user_2.profile.patient
        appointment_2 = AppointmentFactory(patient=patient_2, doctor=self.appointment.doctor)

        self.client.force_login(self.patient_user)
        response = self.client.get(self.url)
        response_data = response.json()['results']
        self.assertEqual(1, len(response_data))
        self.assertEqual(
            self.EXPECTED_APPOINTMENT_LIST_KEYS, response_data[0].keys(),
        )

    def test_filter_by_subsidiary_ids(self):
        subsidiary_1 = self.appointment.subsidiary
        subsidiary_2 = SubsidiaryFactory()
        appointment_2 = AppointmentFactory(
            patient=self.patient, subsidiary=subsidiary_2, status=AppointmentStatus.PLANNED
        )
        self.client.force_login(self.patient_user)

        response = self.client.get(self.url, {'subsidiary_ids': [subsidiary_1.id]})
        response_data = response.json()['results']
        self.assertEqual(1, len(response_data))
        self.assertEqual(self.appointment.id, response_data[0]['id'])

        response = self.client.get(self.url, {'subsidiary_ids': [subsidiary_2.id]})
        response_data = response.json()['results']
        self.assertEqual(1, len(response_data))
        self.assertEqual(appointment_2.id, response_data[0]['id'])

    def test_filter_by_doctor_ids(self):
        doctor_1 = self.appointment.doctor
        doctor_2 = DoctorFactory()
        appointment_2 = AppointmentFactory(
            patient=self.patient, doctor=doctor_2, status=AppointmentStatus.PLANNED
        )
        self.client.force_login(self.patient_user)

        response = self.client.get(self.url, {'doctor_ids': [doctor_1.id]})
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        response_data = response.json()['results']
        self.assertEqual(1, len(response_data))
        self.assertEqual(self.appointment.id, response_data[0]['id'])

        response = self.client.get(self.url, {'doctor_ids': [doctor_2.id]})
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        response_data = response.json()['results']
        self.assertEqual(1, len(response_data))
        self.assertEqual(appointment_2.id, response_data[0]['id'])

    def test_filter_by_service_ids(self):
        service_1 = self.appointment.service
        service_2 = ServiceFactory()

        appointment_2 = AppointmentFactory(
            patient=self.patient, service=service_2, status=AppointmentStatus.PLANNED
        )
        self.client.force_login(self.patient_user)

        response = self.client.get(self.url, {'service_ids': [service_1.id]})
        response_data = response.json()['results']
        self.assertEqual(1, len(response_data))
        self.assertEqual(self.appointment.id, response_data[0]['id'])
        self.assertEqual(service_1.id, response_data[0]['service']['id'])

        response = self.client.get(self.url, {'service_ids': [service_2.id]})
        response_data = response.json()['results']
        self.assertEqual(1, len(response_data))
        self.assertEqual(appointment_2.id, response_data[0]['id'])
        self.assertEqual(service_2.id, response_data[0]['service']['id'])

    def test_filter_by_status__canceled_by_patient(self):
        canceled_by_patient = AppointmentFactory(
            patient=self.patient, status=AppointmentStatus.CANCELED_BY_PATIENT
        )
        canceled_by_moderator = AppointmentFactory(
            patient=self.patient, status=AppointmentStatus.CANCELED_BY_MODERATOR
        )
        self.client.force_login(self.patient_user)

        response = self.client.get(
            self.url, {'status_code': [AppointmentStatus.CANCELED_BY_PATIENT]}
        )
        self.check_status_code(
            response, status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            {
                "api_errors": [
                    {
                        "code": "validation_error",
                        "title": "Invalid status value. Available values: {1, 2, 40, 10, 50, 20, 22, 23, 60, 30}",
                        "source": {"parameter": "status_code"},
                    }
                ],
                "status_code": [
                    "Invalid status value. Available values: {1, 2, 40, 10, 50, 20, 22, 23, 60, 30}"
                ],
            },
            response.json(),
        )

    def test_filter_by_status__canceled_by_moderator(self):
        canceled_by_moderator = AppointmentFactory(
            patient=self.patient, status=AppointmentStatus.CANCELED_BY_MODERATOR
        )
        self.client.force_login(self.patient_user)

        response = self.client.get(
            self.url, {'status_code': [AppointmentStatus.CANCELED_BY_MODERATOR]}
        )
        response_data = response.json()['results']
        self.assertEqual(1, len(response_data))
        self.assertEqual(canceled_by_moderator.id, response_data[0]['id'])

    def test_filter_by_service_ids_and_doctor_ids(self):
        self.client.force_login(self.patient_user)

        response = self.client.get(self.url, {'service_ids': [15], 'doctor_ids': [18]})
        self.assertEqual(status.HTTP_200_OK, response.status_code)

    def test_filter_by_future_and_past(self):
        self.client.force_login(self.patient_user)

        response = self.client.get(self.url, {ONLY_FUTURE: True, ONLY_PAST: True})
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(
            {
                'api_errors': [
                    {
                        'code': 'validation_error',
                        'title': 'only one of "only_future" OR "only_past" can be in params',
                    }
                ],
                'non_field_errors': ['only one of "only_future" OR "only_past" can be in params'],
            },
            response.json(),
        )

    def test_filter_by_future(self):
        past_appointment = AppointmentFactory(
            patient=self.patient,
            start=timezone.now() - timedelta(days=5, hours=10),
            end=timezone.now() - timedelta(days=5, hours=9),
            status=AppointmentStatus.PLANNED,
        )
        self.appointment.start = timezone.now() + timedelta(hours=9)
        self.appointment.end = timezone.now() + timedelta(hours=10)
        self.appointment.save()
        self.client.force_login(self.patient_user)

        response = self.client.get(self.url, {ONLY_FUTURE: True})
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        response_data = response.json()['results']
        self.assertEqual(1, len(response_data))
        self.assertEqual(self.appointment.id, response_data[0]['id'])

    def test_filter_by_past(self):
        future_appointment = AppointmentFactory(
            patient=self.patient,
            start=timezone.now() + timedelta(hours=9),
            end=timezone.now() + timedelta(hours=10),
            status=AppointmentStatus.PLANNED,
        )
        self.appointment.start = timezone.now() - timedelta(days=5, hours=10)
        self.appointment.end = timezone.now() - timedelta(days=5, hours=9)
        self.appointment.save()
        self.client.force_login(self.patient_user)

        response = self.client.get(self.url, {'only_past': True})
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        response_data = response.json()['results']
        self.assertEqual(1, len(response_data))
        self.assertEqual(self.appointment.id, response_data[0]['id'])

    def test_collect_slave_appointments(self):
        slave_patient = PatientFactory()
        new_relation = Relation.objects.create(
            master=self.patient.profile,
            slave=slave_patient.profile,
            can_update_slave_appointments=True,
        )
        slave_appointment = AppointmentFactory(
            patient=slave_patient,
            start=timezone.now() + timedelta(hours=9),
            end=timezone.now() + timedelta(hours=10),
            status=AppointmentStatus.PLANNED,
        )

        self.client.force_login(self.patient_user)
        response = self.client.get(self.url)
        response_data = response.json()['results']
        expected_ids = {self.appointment.id, slave_appointment.id}
        actual_ids = {a['id'] for a in response_data}
        # self.assertEqual(2, len(response_data))
        self.assertEqual(expected_ids, actual_ids)
        self.assertEqual(
            self.EXPECTED_APPOINTMENT_LIST_KEYS, response_data[0].keys(),
        )

    def test_filter_by_related_patient_id(self):
        slave_patient = PatientFactory()
        new_relation = Relation.objects.create(
            master=self.patient.profile,
            slave=slave_patient.profile,
            can_update_slave_appointments=True,
        )
        slave_appointment = AppointmentFactory(
            patient=slave_patient,
            start=timezone.now() + timedelta(hours=9),
            end=timezone.now() + timedelta(hours=10),
            status=AppointmentStatus.PLANNED,
        )
        self.client.force_login(self.patient_user)
        response = self.client.get(self.url, {'related_patient_id': slave_patient.id})
        response_data = response.json()['results']
        expected_ids = [slave_appointment.id]
        actual_ids = [a['id'] for a in response_data]
        self.assertEqual(expected_ids, actual_ids)
        self.assertEqual(
            self.EXPECTED_APPOINTMENT_LIST_KEYS, response_data[0].keys(),
        )


class OneAppointmentViewTest(APITestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.patient_user = PatientUserFactory()
        cls.appointment = AppointmentFactory(
            patient=cls.patient_user.profile.patient, status=AppointmentStatus.PLANNED
        )

    def _get_url(self, appointment_pk):
        return reverse('api.v1:appointments:item', kwargs={'pk': appointment_pk})

    def test_url(self):
        self.assertEqual(
            f'/api/v1/appointments/{self.appointment.pk}', self._get_url(self.appointment.pk)
        )

    def test_access__anonymous(self):
        response = self.client.get(self._get_url(self.appointment.pk))
        self.assertEqual(status.HTTP_401_UNAUTHORIZED, response.status_code)

    def test_access__patient(self):
        self.assertTrue(self.patient_user.is_patient)
        self.client.force_login(self.patient_user)

        response = self.client.get(self._get_url(self.appointment.pk))
        self.assertEqual(status.HTTP_200_OK, response.status_code)

    def test_access__not_patient(self):
        user = UserFactory(profile=DoctorProfileFactory())
        self.assertTrue(user.is_doctor)
        self.client.force_login(user)

        response = self.client.get(self._get_url(self.appointment.pk))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_status__not_found(self):
        self.client.force_login(self.patient_user)
        response = self.client.get(self._get_url(100500))
        self.assertEqual(status.HTTP_404_NOT_FOUND, response.status_code)

    def test_get_single_appointment__valid_data(self):
        self.client.force_login(self.patient_user)
        response = self.client.get(self._get_url(self.appointment.pk))
        response_data = response.json()
        expected_keys = {
            'id',
            'created',
            START,
            HUMAN_START,
            HUMAN_START_DATE,
            HUMAN_START_DATETIME,
            HUMAN_START_DATE_SHORT,
            HUMAN_WEEKDAY,
            HUMAN_START_TIME,
            END,
            PATIENT_ID,
            PATIENT_FULL_NAME,
            DOCTOR,
            SERVICE,
            SUBSIDIARY,
            PRICE,
            'status',
            REASON_TEXT,
            'is_payment_enabled',
            'is_cancel_by_patient_available',
            'is_archived',
            'is_finished',
            'result',
            'has_timeslots',
            'reviews',
            ADDITIONAL_NOTES,
            IS_FOR_WHOLE_DAY,
        }
        actual_keys = response_data.keys()
        self.assertEqual(expected_keys, actual_keys, actual_keys)
        self.assertEqual(
            response_data[PATIENT_FULL_NAME], self.appointment.patient.profile.full_name
        )

    def test_delete__status_not_planned(self):
        self.appointment.status = AppointmentStatus.CANCELED_BY_DOCTOR
        self.appointment.save()
        self.client.force_login(self.patient_user)
        response = self.client.delete(self._get_url(self.appointment.pk))
        data = response.json()
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code, data)
        self.assertEqual(
            {
                'api_errors': [
                    {
                        'code': 'appointment__wrong_status_error',
                        'title': "Ожидается статус 'на модерации/запланирована'; "
                        "сейчас статус: 'отменен доктором'",
                    }
                ]
            },
            data,
        )

    def test_delete__appointment_marked_canceled_by_patient(self):
        self.client.force_login(self.patient_user)
        response = self.client.delete(self._get_url(self.appointment.pk))
        self.assertEqual(status.HTTP_204_NO_CONTENT, response.status_code, response)

        updated_obj: Appointment = Appointment.objects.get(id=self.appointment.id)
        self.assertTrue(updated_obj.is_canceled_by_patient, updated_obj.status)


class CreateAppointmentRequestViewTest(TestCaseCheckStatusCode):
    maxDiff = None
    url = reverse('api.v1:appointments:request_create')

    @classmethod
    def setUpTestData(cls):
        cls.patient_user = PatientUserFactory()
        cls.patient: Patient = cls.patient_user.patient
        cls.doctor_with_timeslots = DoctorFactory(is_timeslots_available_for_patient=True)
        cls.doctor_without_timeslots = DoctorFactory(is_timeslots_available_for_patient=False)
        cls.subsidiary = SubsidiaryFactory()
        cls.service = ServiceFactory()

    @staticmethod
    def _serialize_obj(obj: Appointment):
        return AppointmentListSerializer(instance=obj).data

    def test_url(self):
        self.assertEqual(self.url, '/api/v1/appointments/requests/create')

    def test_access__anonymous(self):
        response = self.client.post(self.url)
        self.assertEqual(status.HTTP_401_UNAUTHORIZED, response.status_code)

    def test_access__patient(self):
        self.assertTrue(self.patient_user.is_patient)
        self.client.force_login(self.patient_user)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_405_METHOD_NOT_ALLOWED, response.status_code)

    def test_access__not_patient(self):
        user = UserFactory(profile=DoctorProfileFactory())
        self.assertTrue(user.is_doctor)
        self.client.force_login(user)

        response = self.client.post(self.url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_fail__bad_start(self):
        test_now = timezone.now()
        start = test_now - timedelta(minutes=10)
        end = test_now + timedelta(minutes=15)
        data = {
            DOCTOR_ID: self.doctor_with_timeslots.id,
            START: start.strftime(APPOINTMENT_DATETIME_FORMAT),
            END: end.strftime(APPOINTMENT_DATETIME_FORMAT),
        }
        self.client.force_login(self.patient_user)
        response = self.client.post(self.url, data=data)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(
            {
                'api_errors': [
                    {
                        'code': 'validation_error',
                        'title': 'Время начала записи должно быть в будущем',
                        'source': {'parameter': START},
                    }
                ],
                START: ['Время начала записи должно быть в будущем'],
            },
            response.json(),
        )

    def test_fail__bad_end(self):
        test_now = timezone.now()
        start = test_now + timedelta(minutes=10)
        end = test_now - timedelta(minutes=15)
        data = {
            DOCTOR_ID: self.doctor_with_timeslots.id,
            START: start.strftime(APPOINTMENT_DATETIME_FORMAT),
            END: end.strftime(APPOINTMENT_DATETIME_FORMAT),
        }
        self.client.force_login(self.patient_user)
        response = self.client.post(self.url, data=data)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(
            {
                'api_errors': [
                    {
                        'code': 'validation_error',
                        'title': 'Время окончания записи должно быть в будущем',
                        'source': {'parameter': END},
                    }
                ],
                END: ['Время окончания записи должно быть в будущем'],
            },
            response.json(),
        )

    def test_fail__only_start_end(self):
        test_now = timezone.now()
        start = test_now + timedelta(minutes=10)
        end = test_now + timedelta(minutes=15)
        data = {
            START: start.strftime(APPOINTMENT_DATETIME_FORMAT),
            END: end.strftime(APPOINTMENT_DATETIME_FORMAT),
        }
        self.client.force_login(self.patient_user)
        response = self.client.post(self.url, data=data)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(
            {
                'api_errors': [
                    {
                        'code': 'appointment_create_error',
                        'title': 'Должен быть указан или врач, или услуга, или текст жалобы',
                    }
                ]
            },
            response.json(),
            response.json(),
        )

    def test_fail__with_doctor__no_time_slots(self):
        test_now = timezone.now()
        start = test_now + timedelta(minutes=10)
        end = test_now + timedelta(minutes=15)
        data = {
            DOCTOR_ID: self.doctor_with_timeslots.id,
            START: start.strftime(APPOINTMENT_DATETIME_FORMAT),
            END: end.strftime(APPOINTMENT_DATETIME_FORMAT),
        }
        self.client.force_login(self.patient_user)
        response = self.client.post(self.url, data=data)
        response_data = response.json()
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code, response_data)
        self.assertEqual(
            {
                "api_errors": [
                    {
                        'code': "no_doctor_free_time_slots",
                        'title': f"Doctor id {self.doctor_with_timeslots.id} has no free time slots from {start.replace(microsecond=0)} to {end.replace(microsecond=0)}",
                    }
                ]
            },
            response_data,
        )

    def test_fail__start_end_intersects_appointment(self):
        test_now = timezone.now()
        start = test_now + timedelta(minutes=10)
        end = test_now + timedelta(minutes=15)
        TimeSlotFactory(start=start, end=end, doctor=self.doctor_with_timeslots)
        AppointmentFactory(
            start=start, end=end, patient=self.patient, doctor=self.doctor_with_timeslots
        )
        data = {
            DOCTOR_ID: self.doctor_with_timeslots.id,
            START: start.strftime(APPOINTMENT_DATETIME_FORMAT),
            END: end.strftime(APPOINTMENT_DATETIME_FORMAT),
        }
        self.client.force_login(self.patient_user)
        response = self.client.post(self.url, data=data)
        response_data = response.json()
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code, response_data)
        self.assertEqual(
            {
                "api_errors": [
                    {
                        'code': "time_is_busy_by_appointment",
                        'title': f"Time from {start.replace(microsecond=0)} to {end.replace(microsecond=0)} is busy",
                    }
                ]
            },
            response_data,
        )

    def test_request_created__with_doctor(self):
        test_now = timezone.now()
        start = test_now + timedelta(minutes=10)
        end = test_now + timedelta(minutes=15)
        TimeSlotFactory(start=start, end=end, doctor=self.doctor_with_timeslots)

        data = {
            DOCTOR_ID: self.doctor_with_timeslots.id,
            START: start.strftime(APPOINTMENT_DATETIME_FORMAT),
            END: end.strftime(APPOINTMENT_DATETIME_FORMAT),
        }
        self.client.force_login(self.patient_user)
        response = self.client.post(self.url, data=data)
        response_data = response.json()
        self.assertEqual(status.HTTP_201_CREATED, response.status_code, response_data)
        new_obj = Appointment.objects.all().latest('id')
        self.assertEqual(self._serialize_obj(new_obj), response_data)
        self.assertTrue(new_obj.is_on_moderation)
        self.assertEqual(self.patient, new_obj.patient)
        self.assertEqual(self.patient, new_obj.author_patient)

    def test_request_created__with_service(self):
        test_now = timezone.now()
        start = test_now + timedelta(minutes=10)
        end = test_now + timedelta(minutes=15)
        new_service = ServiceFactory(is_displayed=True)
        data = {
            SERVICE_ID: new_service.id,
            START: start.strftime(APPOINTMENT_DATETIME_FORMAT),
            END: end.strftime(APPOINTMENT_DATETIME_FORMAT),
        }
        self.client.force_login(self.patient_user)
        response = self.client.post(self.url, data=data)
        response_data = response.json()
        self.assertEqual(status.HTTP_201_CREATED, response.status_code, response_data)
        new_obj = Appointment.objects.all().latest('id')
        self.assertEqual(self._serialize_obj(new_obj), response_data)
        self.assertTrue(new_obj.is_on_moderation)
        self.assertEqual(self.patient, new_obj.patient)
        self.assertEqual(self.patient, new_obj.author_patient)

    def test_request_created__with_complaint(self):
        test_now = timezone.now()
        start = test_now + timedelta(minutes=10)
        end = test_now + timedelta(minutes=15)
        data = {
            REASON_TEXT: 'мне очень плоха',
            START: start.strftime(APPOINTMENT_DATETIME_FORMAT),
            END: end.strftime(APPOINTMENT_DATETIME_FORMAT),
        }
        self.client.force_login(self.patient_user)
        response = self.client.post(self.url, data=data)
        response_data = response.json()
        self.assertEqual(status.HTTP_201_CREATED, response.status_code, response_data)
        new_obj = Appointment.objects.all().latest('id')
        self.assertEqual(self._serialize_obj(new_obj), response_data)
        self.assertTrue(new_obj.is_on_moderation)
        self.assertEqual(self.patient, new_obj.patient)
        self.assertEqual(self.patient, new_obj.author_patient)

    # region with time_slot
    def test_fail__with_doctor__no_time_slot_id(self):
        data = {
            "subsidiary_id": self.subsidiary.id,
            "doctor_id": self.doctor_with_timeslots.id,
            "service_id": self.service.id,
            "time_slot_id": 100500,
            "reason_text": "первая причина это ты",
        }
        self.client.force_login(self.patient_user)
        response = self.client.post(self.url, data=data)
        response_data = response.json()
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code, response_data)
        self.assertEqual(
            {
                'api_errors': [
                    {
                        'code': 'validation_error',
                        'title': 'TimeSlot does not exist',
                        'source': {'parameter': 'time_slot_id'},
                    }
                ],
                'time_slot_id': ['TimeSlot does not exist'],
            },
            response_data,
            response_data,
        )

    def test_fail__with_doctor__timeslot_busy(self):
        timeslot = TimeSlotFactory(doctor=self.doctor_with_timeslots, is_available=False)
        data = {
            "subsidiary_id": self.subsidiary.id,
            "doctor_id": self.doctor_with_timeslots.id,
            "service_id": self.service.id,
            "time_slot_id": timeslot.id,
            "reason_text": "первая причина это ты",
        }
        self.client.force_login(self.patient_user)
        response = self.client.post(self.url, data=data)
        response_data = response.json()
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code, response_data)
        self.assertEqual(
            {
                "api_errors": [
                    {"code": "time_slot_is_busy", "title": f"TimeSlot id {timeslot.id} is busy"}
                ]
            },
            response_data,
            response_data,
        )

    def test_request_created__with_timeslot_id(self):
        test_now = timezone.now()
        start = test_now + timedelta(minutes=10)
        end = test_now + timedelta(minutes=15)
        timeslot = TimeSlotFactory(start=start, end=end, doctor=self.doctor_with_timeslots)
        data = {
            "subsidiary_id": self.subsidiary.id,
            "doctor_id": self.doctor_with_timeslots.id,
            "service_id": self.service.id,
            "time_slot_id": timeslot.id,
            "reason_text": "первая причина это ты",
        }
        self.client.force_login(self.patient_user)
        response = self.client.post(self.url, data=data)
        response_data = response.json()
        self.assertEqual(status.HTTP_201_CREATED, response.status_code, response_data)
        created_obj = Appointment.objects.all().latest('id')
        self.assertEqual(self._serialize_obj(created_obj), response_data)
        self.assertIn(timeslot, created_obj.time_slots.all())
        self.assertIn(created_obj, timeslot.appointments.all())
        updated_slot = TimeSlot.objects.get(id=timeslot.id)
        self.assertFalse(updated_slot.is_available)
        self.assertTrue(created_obj.is_on_moderation)

    # endregion

    # region with Target patient
    def test_target_patient__no_such_patient(self):
        data = {REASON_TEXT: 'мне очень плоха', TARGET_PATIENT_ID: 100500}
        self.client.force_login(self.patient_user)
        response = self.client.post(self.url, data=data)
        response_data = response.json()
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code, response_data)
        self.assertEqual(
            {
                'api_errors': [
                    {
                        'code': 'validation_error',
                        'source': {'parameter': 'target_patient_id'},
                        'title': 'Patient does not exist',
                    }
                ],
                'target_patient_id': ['Patient does not exist'],
            },
            response_data,
            response_data,
        )

    def test_target_patient__wrong_related_patient(self):
        new_patient = PatientFactory()
        data = {REASON_TEXT: 'мне очень плоха', TARGET_PATIENT_ID: new_patient.id}
        self.client.force_login(self.patient_user)
        response = self.client.post(self.url, data=data)
        response_data = response.json()
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code, response_data)
        self.assertEqual(
            {
                'api_errors': [
                    {
                        'code': 'not_valid_target_patient_id__no_related_patients',
                        'title': 'There are no related patient with this target_patient_id for current active patient',
                    }
                ],
            },
            response_data,
            response_data,
        )

    def test_target_patient__wrong_relation_way(self):
        new_patient = PatientFactory()
        relation = Relation.objects.create(
            master=new_patient.profile,
            slave=self.patient.profile,
            can_update_slave_appointments=True,
        )
        data = {REASON_TEXT: 'мне очень плоха', TARGET_PATIENT_ID: new_patient.id}
        self.client.force_login(self.patient_user)
        response = self.client.post(self.url, data=data)
        response_data = response.json()
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code, response_data)
        self.assertEqual(
            {
                'api_errors': [
                    {
                        'code': 'not_valid_target_patient_id__no_related_patients',
                        'title': 'There are no related patient with this target_patient_id for current active patient',
                    }
                ]
            },
            response_data,
            response_data,
        )

    def test_target_patient__parent_patient_has_appointment_for_this_doctor(self):
        child_patient, relation = add_child_relation(self.patient)
        old_appointment: Appointment = AppointmentFactory(patient=self.patient)
        doctor: Doctor = old_appointment.doctor
        data = {DOCTOR_ID: doctor.id, TARGET_PATIENT_ID: child_patient.id}
        self.client.force_login(self.patient_user)
        response = self.client.post(self.url, data=data)
        response_data = response.json()
        self.check_status_code(response, status.HTTP_201_CREATED)
        new_obj = Appointment.objects.get(id=response_data['id'])
        self.assertEqual(self._serialize_obj(new_obj), response_data)
        self.assertTrue(new_obj.is_on_moderation)

    def test_target_patient__parent_patient_has_appointment_for_this_doctor__with_timeslot(self):
        self.assertTrue(self.patient.is_confirmed)
        child_patient, relation = add_child_relation(self.patient)
        doctor: Doctor = DoctorFactory(is_timeslots_available_for_patient=True)
        self.assertFalse(doctor.is_totally_hidden)
        old_appointment: Appointment = AppointmentFactory(
            patient=self.patient,
            doctor=doctor,
            status=AppointmentStatus.ON_MODERATION,
            created_by_type=AppointmentCreatedValues.PATIENT,
        )
        some_timeslot = TimeSlotFactory(
            doctor=doctor, initial_datetime=now_in_default_tz() + timedelta(days=1)
        )
        data = {
            DOCTOR_ID: doctor.id,
            TARGET_PATIENT_ID: child_patient.id,
            TIME_SLOT_ID: some_timeslot.id,
        }
        self.client.force_login(self.patient_user)
        response = self.client.post(self.url, data=data)
        response_data = response.json()
        self.check_status_code(response, status.HTTP_201_CREATED)
        new_obj = Appointment.objects.get(id=response_data['id'])
        self.assertEqual(self._serialize_obj(new_obj), response_data)
        self.assertTrue(new_obj.is_on_moderation)

    # endregion


class TimeSlotViewSetListTest(APITestCase):
    maxDiff = None

    url = reverse('api.v1:appointments:time_slot_list')

    @classmethod
    def setUpTestData(cls):
        cls.patient_user = PatientUserFactory()
        cls.patient = cls.patient_user.profile.patient
        cls.doctor = DoctorFactory(is_timeslots_available_for_patient=True)
        cls.subsidiary = SubsidiaryFactory()

    def setUp(self) -> None:
        self.time_slot: TimeSlot = TimeSlotFactory(
            initial_datetime=timezone.now() + timedelta(days=1),
            doctor=self.doctor,
            subsidiary=self.subsidiary,
            is_available=True,
        )

    @staticmethod
    def _serialize_obj(obj: TimeSlot):
        return TimeSlotSerializer(instance=obj).data

    def test_url(self):
        self.assertEqual(
            f'/api/v1/appointments/available_time_slots', self.url,
        )

    def test_access__anonymous(self):
        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_401_UNAUTHORIZED, response.status_code)

    def test_access__patient(self):
        self.assertTrue(self.patient_user.is_patient)
        self.client.force_login(self.patient_user)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)

    def test_access__not_patient(self):
        user = UserFactory(profile=DoctorProfileFactory())
        self.assertTrue(user.is_doctor)
        self.client.force_login(user)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_data__no_time_slots(self):
        user = PatientUserFactory()
        self.time_slot.delete()
        self.assertFalse(TimeSlot.objects.exists())

        self.client.force_login(user)
        response = self.client.get(self.url)
        response_data = response.json()
        self.assertEqual(status.HTTP_200_OK, response.status_code, response_data)
        self.assertEqual([], response_data['results'])

    def test_data__filter_is_available(self):
        self.time_slot.mark_available()
        self.client.force_login(self.patient_user)
        response = self.client.get(self.url, {'is_available': True})
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        response_data = response.json()['results']
        self.assertEqual(1, len(response_data))
        self.assertEqual(self.time_slot.id, response_data[0]['id'])

        time_slot_2 = TimeSlotFactory(
            doctor=self.doctor, subsidiary=self.subsidiary, is_available=False
        )
        # dont show non available time_slots
        response = self.client.get(self.url, {'is_available': False})
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        response_data = response.json()['results']
        self.assertEqual(1, len(response_data))
        self.assertEqual(self.time_slot.id, response_data[0]['id'])

    def test_data__filter_by_doctor_id(self):
        self.client.force_login(self.patient_user)
        doctor_1 = self.doctor

        response = self.client.get(self.url, {DOCTOR_ID: doctor_1.id})
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        response_data = response.json()['results']
        self.assertEqual(1, len(response_data))
        self.assertEqual(self.time_slot.id, response_data[0]['id'])

        doctor_2 = DoctorFactory()
        time_slot_2 = TimeSlotFactory(
            doctor=doctor_2,
            subsidiary=self.subsidiary,
            initial_datetime=timezone.now() + timedelta(days=1),
        )
        response = self.client.get(self.url, {DOCTOR_ID: doctor_2.id})
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        response_data = response.json()['results']
        self.assertEqual(1, len(response_data))
        self.assertEqual(time_slot_2.id, response_data[0]['id'])

    @freeze_time('2020-01-09')
    def test_data__filter_by_start_date__past(self):
        self.client.force_login(self.patient_user)
        slot_1 = TimeSlotFactory(start=datetime(2020, 1, 9, 15), end=datetime(2020, 1, 9, 16),)
        response = self.client.get(self.url, {'start_date': '2020-01-08'})
        data = response.json()
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code, data)
        self.assertEqual(
            {
                "api_errors": [
                    {
                        "code": "validation_error",
                        "title": "Invalid value. Must be today or future date",
                        "source": {"parameter": "start_date"},
                    }
                ],
                "start_date": ["Invalid value. Must be today or future date"],
            },
            data,
        )

    @freeze_time('2020-01-10')
    def test_data__filter_by_start_date(self):
        self.client.force_login(self.patient_user)
        self.time_slot.delete()
        slot_1 = TimeSlotFactory(start=datetime(2020, 1, 10, 15), end=datetime(2020, 1, 10, 16),)
        slot_2 = TimeSlotFactory(start=datetime(2020, 1, 11, 15), end=datetime(2020, 1, 11, 16),)

        response = self.client.get(self.url, {'start_date': '2020-01-10'})
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        response_data = response.json()['results']
        self.assertEqual(1, len(response_data))
        self.assertEqual(slot_1.id, response_data[0]['id'])

        response = self.client.get(self.url, {'start_date': '2020-01-11'})
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        response_data = response.json()['results']
        self.assertEqual(1, len(response_data))
        self.assertEqual(slot_2.id, response_data[0]['id'])
