import mock
from django.test import override_settings
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from apps.appointments.constants import (
    AppointmentStatus,
    APPOINTMENT_ID,
    RELATED_PATIENT_FULL_NAME,
    ADDITIONAL_NOTES,
    IS_FOR_WHOLE_DAY,
    START,
    HUMAN_START,
    HUMAN_START_DATE,
    HUMAN_START_DATE_SHORT,
    HUMAN_WEEKDAY,
    HUMAN_START_TIME,
    END,
    PATIENT_ID,
    PATIENT_FULL_NAME,
    DOCTOR,
    SERVICE,
    SUBSIDIARY,
    DOCTOR_ID,
    HUMAN_START_DATETIME,
)
from apps.appointments.factories import AppointmentFactory
from apps.appointments.models import Appointment
from apps.clinics.factories import (
    PatientUserFactory,
    DoctorFactory,
    SubsidiaryFactory,
    ServiceFactory,
    PatientFactory,
)
from apps.clinics.models import Patient
from apps.profiles.factories import UserFactory, DoctorProfileFactory
from apps.profiles.models import User, Relation
from apps.reviews.constants import GRADE
from apps.reviews.models import Review
from apps.reviews.serializers import ReviewPrivateSerializer
from apps.reviews.workflow import ReviewWorkflow


@override_settings(
    CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory'
)
class CreateReviewViewTest(APITestCase):
    maxDiff = None
    url = reverse('api.v1:reviews:create')

    @classmethod
    def setUpTestData(cls):
        cls.patient_user = PatientUserFactory()
        cls.patient = cls.patient_user.patient
        cls.doctor_with_timeslots = DoctorFactory(is_timeslots_available_for_patient=True)
        cls.doctor_without_timeslots = DoctorFactory(is_timeslots_available_for_patient=False)
        cls.subsidiary = SubsidiaryFactory()
        cls.service = ServiceFactory()

    def setUp(self) -> None:
        self.appointment = AppointmentFactory(
            patient=self.patient, subsidiary=self.subsidiary, status=AppointmentStatus.PLANNED
        )

    @staticmethod
    def _serialize_obj(obj: Review):
        return ReviewPrivateSerializer(instance=obj).data

    def test_url(self):
        self.assertEqual(self.url, '/api/v1/reviews/create')

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

    def test_fail__bad_appointment(self):
        data = {
            APPOINTMENT_ID: 100500,
            GRADE: 4,
            'text': '654654654',
        }
        self.client.force_login(self.patient_user)
        response = self.client.post(self.url, data=data)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(
            {
                'api_errors': [
                    {
                        'code': 'validation_error',
                        'title': 'No appointment found for passed appointment_id',
                    },
                ],
                'non_field_errors': ['No appointment found for passed appointment_id'],
            },
            response.json(),
        )

    def test_fail__no_grade(self):
        data = {
            APPOINTMENT_ID: self.appointment.id,
            'text': '654654654',
        }
        self.client.force_login(self.patient_user)
        response = self.client.post(self.url, data=data)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(
            {
                'api_errors': [
                    {
                        'code': 'validation_error',
                        'title': "Укажите, пожалуйста, оценку.",
                        'source': {'parameter': 'grade'},
                    }
                ],
                'grade': ["Укажите, пожалуйста, оценку."],
            },
            response.json(),
        )

    def test_fail__bad_grade(self):
        data = {
            APPOINTMENT_ID: self.appointment.id,
            GRADE: 100500,
            'text': '654654654',
        }
        self.client.force_login(self.patient_user)
        response = self.client.post(self.url, data=data)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(
            {
                'api_errors': [
                    {
                        'code': 'validation_error',
                        'title': 'Убедитесь, что это значение меньше либо равно 5.',
                        'source': {'parameter': 'grade'},
                    }
                ],
                'grade': ['Убедитесь, что это значение меньше либо равно 5.'],
            },
            response.json(),
        )

    def test_fail__no_text(self):
        data = {
            APPOINTMENT_ID: self.appointment.id,
            GRADE: 2,
        }
        self.client.force_login(self.patient_user)
        response = self.client.post(self.url, data=data)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(
            {
                'api_errors': [
                    {
                        'code': 'validation_error',
                        'title': "Напишите, пожалуйста, комментарий.",
                        'source': {'parameter': 'text'},
                    }
                ],
                'text': ["Напишите, пожалуйста, комментарий."],
            },
            response.json(),
        )

    def test_fail__empty_text(self):
        data = {
            APPOINTMENT_ID: self.appointment.id,
            GRADE: 2,
            'text': '',
        }
        self.client.force_login(self.patient_user)
        response = self.client.post(self.url, data=data)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(
            {
                'api_errors': [
                    {
                        'code': 'validation_error',
                        'title': 'Напишите, пожалуйста, комментарий. Он не может быть пустым.',
                        'source': {'parameter': 'text'},
                    }
                ],
                'text': ['Напишите, пожалуйста, комментарий. Он не может быть пустым.'],
            },
            response.json(),
        )

    def test_fail__bad_appointment_id(self):
        data = {
            APPOINTMENT_ID: '',
            GRADE: 3,
            'text': '654654654',
        }
        self.client.force_login(self.patient_user)
        response = self.client.post(self.url, data=data)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(
            {
                'api_errors': [
                    {
                        'code': 'validation_error',
                        'title': 'Введите правильное число.',
                        'source': {'parameter': 'appointment_id'},
                    }
                ],
                'appointment_id': ['Введите правильное число.'],
            },
            response.json(),
        )

    def test_fail__appointment_without_doctor(self):
        appointment = AppointmentFactory(patient=self.patient)
        appointment.doctor = None
        appointment.save()
        data = {
            APPOINTMENT_ID: appointment.id,
            GRADE: 3,
            'text': '654654654',
        }
        self.client.force_login(self.patient_user)
        response = self.client.post(self.url, data=data)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        expected_err_text = (
            "Для этой записи не указан доктор. Мы уже знаем о проблеме, решим в ближайшее время."
        )
        self.assertEqual(
            {
                'api_errors': [{'code': 'validation_error', 'title': expected_err_text,}],
                'non_field_errors': [expected_err_text],
            },
            response.json(),
        )

    def test_fail__for_related_patients_appointment(self):
        slave_patient = PatientFactory()
        new_relation = Relation.objects.create(
            master=slave_patient.profile,
            slave=self.patient.profile,
            can_update_slave_appointments=True,
        )
        slave_appointment = AppointmentFactory(
            patient=slave_patient, status=AppointmentStatus.FINISHED,
        )
        data = {
            APPOINTMENT_ID: slave_appointment.id,
            GRADE: 3,
            'text': 'test_fail__for_related_patients_appointment',
        }
        self.client.force_login(self.patient_user)
        response = self.client.post(self.url, data=data)
        response_data = response.json()
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code, response_data)
        expected_err_text = "No appointment found for passed appointment_id"
        self.assertEqual(
            {
                'api_errors': [{'code': 'validation_error', 'title': expected_err_text,}],
                'non_field_errors': [expected_err_text],
            },
            response.json(),
        )

    def test_review_created(self):
        data = {
            APPOINTMENT_ID: self.appointment.id,
            GRADE: 2,
            'text': 'ну такое',
        }
        self.client.force_login(self.patient_user)
        response = self.client.post(self.url, data=data)
        response_data = response.json()
        self.assertEqual(status.HTTP_201_CREATED, response.status_code, response_data)
        new_obj = Review.objects.all().latest('id')
        self.assertEqual(self._serialize_obj(new_obj), response_data)

    def test_review_created__for_related_patients_appointment(self):
        slave_patient = PatientFactory()
        new_relation = Relation.objects.create(
            master=self.patient.profile,
            slave=slave_patient.profile,
            can_update_slave_appointments=True,
        )
        slave_appointment = AppointmentFactory(
            patient=slave_patient, status=AppointmentStatus.FINISHED,
        )
        data = {
            'appointment_id': slave_appointment.id,
            'grade': 3,
            'text': 'test_review_created__for_related_patients_appointment',
        }
        self.client.force_login(self.patient_user)
        response = self.client.post(self.url, data=data)
        response_data = response.json()
        self.assertEqual(status.HTTP_201_CREATED, response.status_code, response_data)
        new_obj = Review.objects.all().latest('id')
        self.assertEqual(self._serialize_obj(new_obj), response_data)


@override_settings(
    CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory'
)
class AppointmentWithReviewTest(APITestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.patient_user: User = PatientUserFactory()
        cls.patient: Patient = cls.patient_user.patient
        cls.appointment: Appointment = AppointmentFactory(
            patient=cls.patient_user.profile.patient, status=AppointmentStatus.PLANNED
        )
        cls.EXPECTED_APPOINTMENT_KEYS = {
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
            'price',
            'status',
            'reason_text',
            'is_payment_enabled',
            'is_cancel_by_patient_available',
            'is_finished',
            'is_archived',
            'result',
            'has_timeslots',
            'reviews',
            ADDITIONAL_NOTES,
            IS_FOR_WHOLE_DAY,
        }

    def _get_url(self, appointment_pk):
        return reverse('api.v1:appointments:item', kwargs={'pk': appointment_pk})

    def test_reviews__no_review_provided(self):
        self.assertFalse(self.appointment.has_reviews)
        self.client.force_login(self.patient_user)
        response = self.client.get(self._get_url(self.appointment.pk))
        response_data = response.json()
        actual_keys = response_data.keys()

        self.assertTrue('reviews' in actual_keys)

        self.assertEqual(self.EXPECTED_APPOINTMENT_KEYS, actual_keys, actual_keys)
        actual_reviews = response_data.get('reviews')
        self.assertEqual([], actual_reviews)

    def test_reviews__with_review_provided(self):
        review = ReviewWorkflow.create_by_patient(
            patient=self.patient,
            data={GRADE: 2, "text": 'lol', APPOINTMENT_ID: self.appointment.id},
        )
        self.assertTrue(review.id)
        self.assertFalse(review.is_displayed)

        self.appointment = self.appointment.reload()
        self.assertTrue(self.appointment.has_reviews)

        self.client.force_login(self.patient_user)
        response = self.client.get(self._get_url(self.appointment.pk))
        response_data = response.json()
        actual_keys = response_data.keys()

        self.assertTrue('reviews' in actual_keys)
        self.assertEqual(self.EXPECTED_APPOINTMENT_KEYS, actual_keys, actual_keys)
        actual_reviews = response_data.get('reviews')
        self.assertIsNotNone(actual_reviews)
        expected_reviews = [
            {
                'id': review.id,
                'created': mock.ANY,
                GRADE: review.grade,
                'doctor_id': review.doctor_id,
                'doctor_full_name': review.doctor.short_full_name,
                'text': 'lol',
                "author_first_name": self.patient.profile.first_name,
            }
        ]
        self.assertEqual(expected_reviews, actual_reviews)


@override_settings(
    CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory'
)
class AppointmentListWithReviewTest(APITestCase):
    maxDiff = None

    url = reverse('api.v1:appointments:list')

    @classmethod
    def setUpTestData(cls):
        cls.patient_user: User = PatientUserFactory()
        cls.patient: Patient = cls.patient_user.patient
        cls.appointment: Appointment = AppointmentFactory(
            patient=cls.patient_user.profile.patient, status=AppointmentStatus.PLANNED
        )
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
            SERVICE,
            SUBSIDIARY,
            'status',
            'reason_text',
            'is_payment_enabled',
            'is_cancel_by_patient_available',
            'is_archived',
            'is_finished',
            'price',
            'has_timeslots',
            GRADE,
            RELATED_PATIENT_FULL_NAME,
            IS_FOR_WHOLE_DAY,
        }

    def test_data__no_reviews(self):
        self.client.force_login(self.patient_user)
        response = self.client.get(self.url)
        response_data = response.json()['results']
        self.assertEqual(1, len(response_data))
        self.assertEqual(
            self.EXPECTED_APPOINTMENT_LIST_KEYS, response_data[0].keys(),
        )
        self.assertIsNone(response_data[0][GRADE])

    def test_data__with_reviews(self):
        self.client.force_login(self.patient_user)
        print(f"{self.appointment.id=}")
        print(f"{self.patient.id=}")
        review = ReviewWorkflow.create_by_patient(
            patient=self.patient,
            data={GRADE: 2, "text": 'lol', APPOINTMENT_ID: self.appointment.id},
        )
        self.assertTrue(review.id)

        response = self.client.get(self.url)
        response_data = response.json()['results']
        self.assertEqual(1, len(response_data))
        actual_keys = response_data[0].keys()
        self.assertEqual(self.EXPECTED_APPOINTMENT_LIST_KEYS, actual_keys, actual_keys)
        self.assertEqual(2, response_data[0][GRADE])
