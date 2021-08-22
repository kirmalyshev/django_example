from datetime import timedelta

import mock
from django.conf import settings
from django.test import TestCase
from django.utils import timezone

from apps.appointments.constants import (
    AppointmentStatus,
    TIME_SLOT_ID,
    DOCTOR_ID,
    TARGET_PATIENT_ID,
    AUTHOR_PATIENT,
    AppointmentCreatedValues,
)
from apps.appointments.exceptions import AppointmentCreateError
from apps.appointments.factories import (
    TimeSlotFactory,
    AppointmentFactory,
)
from apps.appointments.models import Appointment
from apps.appointments.selectors import TimeSlots, AllAppointmentsSelector
from apps.appointments.workflows import (
    TimeSlotWorkflow,
    AppointmentWorkflow,
)
from apps.clinics.factories import PatientFactory, DoctorFactory, SubsidiaryFactory, ServiceFactory
from apps.clinics.models import Patient, Doctor
from apps.clinics.test_tools import add_child_relation
from apps.core.utils import now_in_default_tz
from apps.feature_toggles.constants import IS_RELATED_PATIENTS_ENABLED
from apps.feature_toggles.ops_features import is_related_patients_enabled
from apps.profiles.models import Relation


class AppointmentWorkflowTest(TestCase):
    workflow = AppointmentWorkflow

    @classmethod
    def setUpTestData(cls):
        cls.patient: Patient = PatientFactory(is_confirmed=True)
        cls.doctor = DoctorFactory()
        cls.subsidiary = SubsidiaryFactory()
        cls.service = ServiceFactory()
        cls.appointment: Appointment = AppointmentFactory(
            patient=cls.patient, status=AppointmentStatus.ON_MODERATION
        )

    def _get_updated_appointment(self, obj_id=None) -> Appointment:
        if not obj_id:
            return AllAppointmentsSelector.get_by_id(self.appointment.id)
        return AllAppointmentsSelector.get_by_id(obj_id)

    # region Cancel by patient
    def test_cancel_by_patient__with_timeslot(self):
        time_slot = TimeSlotFactory(doctor=self.doctor, subsidiary=self.subsidiary)
        TimeSlotWorkflow.link_with_appointment(
            time_slot, self.appointment,
        )

        self.workflow.cancel_by_patient(
            self.appointment, self.patient,
        )

        # all timeslots should stay linked with appointment
        updated_time_slot = TimeSlots().all().get(id=time_slot.id)
        self.assertFalse(updated_time_slot.is_available)
        self.assertEqual(1, updated_time_slot.appointments.count())
        updated_appointment_request = self._get_updated_appointment()
        self.assertEqual(1, updated_appointment_request.time_slots.count())

    def test_cancel_by_patient__appointment_belongs_to_slave(self):
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

        self.workflow.cancel_by_patient(
            slave_appointment, self.patient,
        )
        updated_appointment = self._get_updated_appointment(slave_appointment.id)
        self.assertTrue(updated_appointment.is_canceled_by_patient)
        self.assertFalse(updated_appointment.is_cancel_by_patient_available)

    # endregion
    # region Create by patient
    def test_create__doctor_service_subsidiary(self):
        appointment = self.workflow.create_by_patient(
            self.patient,
            {
                'subsidiary_id': self.subsidiary.id,
                'doctor_id': self.doctor.id,
                'service_id': self.service.id,
            },
        )
        latest_obj = AllAppointmentsSelector().all().latest('created')
        self.assertEqual(appointment, latest_obj)
        self.assertTrue(appointment.is_on_moderation)
        self.assertEqual(appointment.service, self.service)
        self.assertEqual(appointment.subsidiary, self.subsidiary)
        self.assertEqual(appointment.doctor, self.doctor)
        self.assertIsNone(appointment.start)
        self.assertIsNone(appointment.end)
        self.assertIsNone(appointment.reason_text)
        self.assertEqual(self.patient, appointment.patient)
        self.assertEqual(appointment.patient, appointment.author_patient)

    def test_create__without_any_data(self):
        with self.assertRaises(AppointmentCreateError) as err_context:
            appointment = self.workflow.create_by_patient(self.patient, {})
        exception = err_context.exception
        self.assertEqual("appointment_create_error", exception.code)
        self.assertEqual(
            "Должен быть указан или врач, или услуга, или текст жалобы", exception.title,
        )

    def test_create__only_reason_text(self):
        appointment = self.workflow.create_by_patient(self.patient, {'reason_text': "i need halp"})
        latest_obj = AllAppointmentsSelector().all().latest('created')
        self.assertEqual(appointment, latest_obj)
        self.assertTrue(appointment.is_on_moderation)
        self.assertIsNone(appointment.service)
        self.assertIsNone(appointment.subsidiary)
        self.assertIsNone(appointment.doctor)
        self.assertEqual("i need halp", appointment.reason_text)
        self.assertIsNone(appointment.start)
        self.assertIsNone(appointment.end)
        self.assertEqual(self.patient, appointment.patient)
        self.assertEqual(appointment.patient, appointment.author_patient)

    def test_create__only_doctor(self):
        appointment = self.workflow.create_by_patient(self.patient, {'doctor_id': self.doctor.id})
        latest_obj = AllAppointmentsSelector().all().latest('created')
        self.assertEqual(appointment, latest_obj)
        self.assertTrue(appointment.is_on_moderation)
        self.assertEqual(appointment.doctor, self.doctor)
        self.assertIsNone(appointment.service)
        self.assertIsNone(appointment.subsidiary)
        self.assertIsNone(appointment.reason_text)
        self.assertIsNone(appointment.start)
        self.assertIsNone(appointment.end)
        self.assertEqual(self.patient, appointment.patient)
        self.assertEqual(appointment.patient, appointment.author_patient)

    def test_create__timeslots_forbidden_for_doctor__with_timeslots(self):
        no_timeslots_doctor = DoctorFactory(is_timeslots_available_for_patient=False)
        timeslot = TimeSlotFactory(doctor=no_timeslots_doctor)
        with self.assertRaises(AppointmentCreateError) as err_context:
            appointment = self.workflow.create_by_patient(
                self.patient, {DOCTOR_ID: no_timeslots_doctor.id, TIME_SLOT_ID: timeslot.id}
            )
        exception = err_context.exception
        self.assertEqual("timeslots_for_doctor_unavailable", exception.code)
        self.assertEqual(
            "Для данного доктора нельзя записываться на какое-то конкретное время", exception.title,
        )

    def test_create__timeslots_forbidden_for_doctor__no_timeslots(self):
        no_timeslots_doctor = DoctorFactory(is_timeslots_available_for_patient=False)
        appointment = self.workflow.create_by_patient(
            self.patient, {DOCTOR_ID: no_timeslots_doctor.id}
        )
        latest_obj = AllAppointmentsSelector().all().latest('created')
        self.assertEqual(appointment, latest_obj)
        self.assertTrue(appointment.is_on_moderation)
        self.assertEqual(appointment.doctor, no_timeslots_doctor)
        self.assertIsNone(appointment.service)
        self.assertIsNone(appointment.subsidiary)
        self.assertIsNone(appointment.reason_text)
        self.assertIsNone(appointment.start)
        self.assertIsNone(appointment.end)
        self.assertEqual(self.patient, appointment.patient)
        self.assertEqual(appointment.patient, appointment.author_patient)

    def test_create__for_master__child_has_appointments_for_this_doctor(self):
        child_patient, relation = add_child_relation(self.patient)
        old_appointment: Appointment = AppointmentFactory(
            patient=child_patient,
            status=AppointmentStatus.ON_MODERATION,
            created_by_type=AppointmentCreatedValues.PATIENT,
        )
        doctor: Doctor = old_appointment.doctor

        appointment = self.workflow.create_by_patient(self.patient, {DOCTOR_ID: doctor.id})
        self.assertTrue(appointment.is_on_moderation)
        self.assertEqual(appointment.doctor, doctor)
        self.assertIsNone(appointment.service)
        self.assertIsNone(appointment.subsidiary)
        self.assertIsNone(appointment.reason_text)
        self.assertIsNone(appointment.start)
        self.assertIsNone(appointment.end)
        self.assertEqual(appointment.patient, self.patient)
        self.assertEqual(self.patient, appointment.author_patient)

    # region with target patient
    def test_create__with_target_patient__no_such_target_patient(self):
        with self.assertRaises(AppointmentCreateError) as err_context:
            appointment = self.workflow.create_by_patient(
                self.patient, {DOCTOR_ID: self.doctor.id, TARGET_PATIENT_ID: 100500}
            )
        exception = err_context.exception
        self.assertEqual("not_valid_target_patient_id__no_related_patients", exception.code)
        self.assertEqual(
            "There are no related patient with this target_patient_id for current active patient",
            exception.title,
        )

    def test_create__with_target_patient__ok(self):
        child_patient: Patient = PatientFactory()
        relation = Relation.objects.create(
            master=self.patient.profile,
            slave=child_patient.profile,
            can_update_slave_appointments=True,
        )
        appointment = self.workflow.create_by_patient(
            self.patient, {DOCTOR_ID: self.doctor.id, TARGET_PATIENT_ID: child_patient.id}
        )

        latest_obj = AllAppointmentsSelector().all().latest('created')
        self.assertEqual(appointment, latest_obj)
        self.assertTrue(appointment.is_on_moderation)
        self.assertEqual(appointment.doctor, self.doctor)
        self.assertIsNone(appointment.service)
        self.assertIsNone(appointment.subsidiary)
        self.assertIsNone(appointment.reason_text)
        self.assertIsNone(appointment.start)
        self.assertIsNone(appointment.end)
        self.assertEqual(appointment.patient, child_patient)
        self.assertEqual(self.patient, appointment.author_patient)

    def test_create__with_target_patient__wrong_relation_way(self):
        child_patient: Patient = PatientFactory()
        relation = Relation.objects.create(
            master=child_patient.profile,
            slave=self.patient.profile,
            can_update_slave_appointments=True,
        )
        with self.assertRaises(AppointmentCreateError) as err_context:
            appointment = self.workflow.create_by_patient(
                self.patient, {DOCTOR_ID: self.doctor.id, TARGET_PATIENT_ID: child_patient.id}
            )
        exception = err_context.exception
        self.assertEqual("not_valid_target_patient_id__no_related_patients", exception.code)
        self.assertEqual(
            "There are no related patient with this target_patient_id for current active patient",
            exception.title,
        )

    def test_create__with_target_patient__related_patients_not_allowed(self):
        child_patient: Patient = PatientFactory()
        relation = Relation.objects.create(
            master=self.patient.profile,
            slave=child_patient.profile,
            can_update_slave_appointments=True,
        )
        with mock.patch.dict(settings.OPS_FEATURES, {IS_RELATED_PATIENTS_ENABLED: False}):
            # print(f"{is_related_patients_enabled.is_enabled=}")
            # import ipdb; ipdb.set_trace()  # TODO fix
            with self.assertRaises(AppointmentCreateError) as err_context:
                appointment = self.workflow.create_by_patient(
                    self.patient, {DOCTOR_ID: self.doctor.id, TARGET_PATIENT_ID: child_patient.id}
                )
            exception = err_context.exception
            self.assertEqual("not_valid_target_patient_id__wrong_settings", exception.code)
            self.assertEqual(
                "Param is not expected due to inner settings", exception.title,
            )

    def test_create__master_patient_has_appointments_for_this_doctor(self):
        child_patient, relation = add_child_relation(self.patient)
        old_appointment: Appointment = AppointmentFactory(
            patient=self.patient,
            status=AppointmentStatus.ON_MODERATION,
            created_by_type=AppointmentCreatedValues.PATIENT,
        )
        doctor: Doctor = old_appointment.doctor

        appointment = self.workflow.create_by_patient(
            self.patient, {DOCTOR_ID: doctor.id, TARGET_PATIENT_ID: child_patient.id}
        )
        self.assertTrue(appointment.is_on_moderation)
        self.assertEqual(appointment.doctor, doctor)
        self.assertIsNone(appointment.service)
        self.assertIsNone(appointment.subsidiary)
        self.assertIsNone(appointment.reason_text)
        self.assertIsNone(appointment.start)
        self.assertIsNone(appointment.end)
        self.assertEqual(appointment.patient, child_patient)
        self.assertEqual(self.patient, appointment.author_patient)

    def test_create__master_patient_has_appointments_for_this_doctor__with_timeslot(self):
        child_patient, relation = add_child_relation(self.patient)
        doctor: Doctor = DoctorFactory(is_timeslots_available_for_patient=True)
        old_appointment: Appointment = AppointmentFactory(
            patient=self.patient,
            doctor=doctor,
            status=AppointmentStatus.ON_MODERATION,
            created_by_type=AppointmentCreatedValues.PATIENT,
        )
        some_timeslot = TimeSlotFactory(
            doctor=doctor, initial_datetime=now_in_default_tz() + timedelta(days=1)
        )

        appointment = self.workflow.create_by_patient(
            self.patient,
            {
                DOCTOR_ID: doctor.id,
                TARGET_PATIENT_ID: child_patient.id,
                TIME_SLOT_ID: some_timeslot.id,
            },
        )
        self.assertTrue(appointment.is_on_moderation)
        self.assertEqual(appointment.doctor, doctor)
        self.assertIsNone(appointment.service)
        self.assertIsNone(appointment.subsidiary)
        self.assertIsNone(appointment.reason_text)
        self.assertIsNotNone(appointment.start)
        self.assertIsNotNone(appointment.end)
        self.assertEqual(appointment.patient, child_patient)
        self.assertEqual(self.patient, appointment.author_patient)

    def test_create__child_patient_has_appointments_for_this_doctor(self):
        child_patient, relation = add_child_relation(self.patient)
        old_appointment: Appointment = AppointmentFactory(
            patient=child_patient,
            status=AppointmentStatus.ON_MODERATION,
            created_by_type=AppointmentCreatedValues.PATIENT,
        )
        doctor: Doctor = old_appointment.doctor

        with self.assertRaises(AppointmentCreateError) as err_context:
            appointment = self.workflow.create_by_patient(
                self.patient, {DOCTOR_ID: doctor.id, TARGET_PATIENT_ID: child_patient.id}
            )
        exception = err_context.exception
        self.assertEqual("already_has_appointment_to_doctor", exception.code)
        self.assertEqual(
            "Указанный пациент уже записывался сегодня к этому доктору. Дождитесь обработки вашей заявки",
            exception.title,
        )

    def test_create__child_patient_has_appointments_for_this_doctor__with_timeslot(self):
        child_patient, relation = add_child_relation(self.patient)
        doctor: Doctor = DoctorFactory(is_timeslots_available_for_patient=True)
        old_appointment: Appointment = AppointmentFactory(
            patient=child_patient,
            doctor=doctor,
            status=AppointmentStatus.ON_MODERATION,
            created_by_type=AppointmentCreatedValues.PATIENT,
        )
        some_timeslot = TimeSlotFactory(
            doctor=doctor, initial_datetime=now_in_default_tz() + timedelta(days=1)
        )

        with self.assertRaises(AppointmentCreateError) as err_context:
            appointment = self.workflow.create_by_patient(
                self.patient,
                {
                    DOCTOR_ID: doctor.id,
                    TARGET_PATIENT_ID: child_patient.id,
                    TIME_SLOT_ID: some_timeslot.id,
                },
            )
        exception = err_context.exception
        self.assertEqual("already_has_appointment_to_doctor", exception.code)
        self.assertEqual(
            "Указанный пациент уже записывался сегодня к этому доктору. Дождитесь обработки вашей заявки",
            exception.title,
        )

    # TODO add tests about related patients
    # endregion
    # endregion

    # endregion

    def test_finish__marked_finished(self):
        # on_moderation
        self.workflow.finish(self.appointment)
        updated_obj: Appointment = self._get_updated_appointment()
        self.assertTrue(updated_obj.is_finished)

        # Planned
        self.appointment.mark_planned(save=True)
        self.workflow.finish(self.appointment)
        updated_obj: Appointment = self._get_updated_appointment()
        self.assertTrue(updated_obj.is_finished)
