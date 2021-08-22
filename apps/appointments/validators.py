import logging
from datetime import datetime
from typing import Dict, Union, Iterable

from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import ugettext_lazy as _

from apps.appointments import selectors
from apps.appointments.constants import (
    AppointmentStatus,
    TIME_SLOT_ID,
    DOCTOR_ID,
    END,
    START,
    APPOINTMENT_ID,
    AUTHOR_PATIENT,
    SERVICE_ID,
    TARGET_PATIENT_ID,
    CreateAppointmentByPatientDict,
)
from apps.appointments.exceptions import (
    WrongStatusError,
    AppointmentWrongStatusError,
    AppointmentCreateError,
    AppointmentRejectError,
    AppointmentApproveError,
    AppointmentError,
    AppointmentWrongOwnerError,
)
from apps.appointments.model_utils import validate_appointment_start_end
from apps.appointments.models import Appointment, BaseAppointment
from apps.appointments.selectors import DoctorTimeSlots, PatientAppointments
from apps.clinics.models import Patient, Doctor
from apps.clinics.selectors import DoctorSelector, PatientSelector
from apps.clinics.utils import PatientUtils
from apps.core.constants import RAISE_ERROR
from apps.feature_toggles.ops_features import is_related_patients_enabled


class BaseAppointmentValidator:
    status_enum = None
    wrong_status_error = WrongStatusError

    @classmethod
    def _validate_start_end(cls, data: Dict) -> None:
        """
        Check if start/end data is valid
        :param data: contains data, passed from serializer
        :raise: apps.appointments.exceptions.AppointmentError
        """
        start = data.get('start')
        end = data.get('end')
        if not start and not end:
            return
        try:
            validate_appointment_start_end(start, end)
        except DjangoValidationError as err:
            raise AppointmentError(err)

    @classmethod
    def _check_time_slot_available(cls, time_slot_id: int, doctor_id: int) -> None:
        time_slots_selector = selectors.DoctorTimeSlots(doctor_id)
        time_slot = time_slots_selector.all().filter(id=time_slot_id).first()
        if not time_slot:
            AppointmentError(
                code='time_slot_does_not_exist', title=_(f'TimeSlot id {time_slot_id} not found'),
            )

        if not time_slot.is_available:
            raise AppointmentError(
                code='time_slot_is_busy', title=_(f'TimeSlot id {time_slot_id} is busy')
            )

    @classmethod
    def _check_time_free_for_doctor(cls, data: Dict) -> None:
        """
        If
        * there's no created appointment for passed time and doctor
        * there're free TimeSlots for doctor
        then everything ok
        :param data: contains data, passed from serializer
        :raises: apps.appointments.exceptions.AppointmentCreateError
        """
        doctor_id = data[DOCTOR_ID]
        time_slot_id = data.get(TIME_SLOT_ID)
        start = data.get(START)
        end = data.get(END)
        if time_slot_id:
            cls._check_time_slot_available(time_slot_id, doctor_id)

        elif start and end:
            doctor_time_slots = selectors.DoctorTimeSlots(doctor_id)

            # 1st, check if doctor has free time_slots
            doctor_has_free_time_slots = doctor_time_slots.free_for_period(start, end).exists()
            if not doctor_has_free_time_slots:
                raise AppointmentCreateError(
                    code='no_doctor_free_time_slots',
                    title=_(f'Doctor id {doctor_id} has no free time slots from {start} to {end}'),
                )

            # 2nd, check if doctor has no appointments
            doctor_appointments = selectors.DoctorAppointments(doctor_id)
            is_appointments_exist = doctor_appointments.has_for_future_period(start=start, end=end)
            if is_appointments_exist:
                raise AppointmentCreateError(
                    code='time_is_busy_by_appointment',
                    title=_(f'Time from {start} to {end} is busy'),
                )

    @classmethod
    def _is_data_valid_for_doctor(cls, data: Dict):
        doctor_id = data[DOCTOR_ID]
        doctor: Doctor = DoctorSelector.get_by_id(doctor_id)
        is_timeslots_available = doctor.is_timeslots_available_for_patient
        if not is_timeslots_available and data.get(TIME_SLOT_ID):
            raise AppointmentCreateError(
                code="timeslots_for_doctor_unavailable",
                title=_(f"Для данного доктора нельзя записываться на какое-то конкретное время"),
            )

    @classmethod
    def _are_there_no_today_appointment_for_doctor(cls, data: Dict, patient: Union[Patient, int]):
        # todo put to feature_toggles
        if isinstance(patient, int):
            patient = PatientSelector.get_by_id(patient)

        doctor_id = data[DOCTOR_ID]
        today_doctor_appointments = (
            PatientAppointments(patient)
            .on_moderation_created_today(patient=patient)
            .filter(doctor_id=doctor_id)
        )
        if today_doctor_appointments.exists():
            raise AppointmentCreateError(
                code="already_has_appointment_to_doctor",
                title=_(
                    f"Указанный пациент уже записывался сегодня к этому доктору. Дождитесь обработки вашей заявки"
                ),
            )

    @classmethod
    def check_valid_status(cls, obj: Appointment, expected_status: Union[int, Iterable]) -> None:
        if isinstance(expected_status, int):
            expected_status = [expected_status]
        valid_statuses = cls.status_enum.VALUES.keys()
        if not set(expected_status).issubset(set(valid_statuses)):
            raise ValueError(
                f"{expected_status} not in valid keys. Possible values:{valid_statuses}"
            )

        if obj.status not in expected_status:
            expected_status_values = "/".join(
                [f"{cls.status_enum.get_display_value(key)}" for key in expected_status]
            )
            actual_status = cls.status_enum.get_display_value(obj.status)
            error_message = _(
                f"Ожидается статус '{expected_status_values}'; сейчас статус: '{actual_status}'"
            )
            raise cls.wrong_status_error(title=error_message)

    @classmethod
    def _check_can_patient_update_appointment(cls, obj: BaseAppointment, patient: Patient) -> None:
        """
        Проверим, может ли данные пациент изменять указанную Запись.
        Может при условиях:
        * или пациенту принадлежит Запись
        * или эта запись принадлежит зависимому пациенту.
        """
        slave_patient_ids = PatientUtils.get_slave_patients_ids(obj.patient)
        allowed_patient_ids = [obj.patient_id] + slave_patient_ids

        if obj.patient_id not in allowed_patient_ids:
            raise AppointmentWrongOwnerError(
                title=_(f'Patient {patient} cannot change this object')
            )


class AppointmentModerationValidator(BaseAppointmentValidator):
    status_enum = AppointmentStatus
    base_error = AppointmentError
    create_error = AppointmentCreateError
    reject_error = AppointmentRejectError
    approve_error = AppointmentApproveError

    @classmethod
    def validate_before_reject(cls, appointment: Appointment, **kwargs) -> None:
        """
        :raises: apps.appointments.exceptions.AppointmentRejectError
        """
        raise_error = kwargs.get(RAISE_ERROR, True)
        try:
            cls.check_valid_status(appointment, cls.status_enum.ON_MODERATION)
        except WrongStatusError as err:
            valid_err = cls.reject_error(title=err.title)
            if raise_error:
                raise valid_err
            else:
                logging.warning(valid_err, extra={APPOINTMENT_ID: appointment.id})

    @classmethod
    def validate_before_approve(cls, appointment: Appointment) -> None:
        """
        :raises: apps.appointments.exceptions.AppointmentApproveError
        """
        try:
            cls.check_valid_status(appointment, cls.status_enum.ON_MODERATION)
        except WrongStatusError as err:
            raise cls.approve_error(title=err.title)

        required_values = {appointment.subsidiary, appointment.doctor}
        if not all(required_values):
            error_message = _("Должны быть указаны врач И филиал")
            raise cls.approve_error(title=error_message)

    @classmethod
    def validate_before_return_to_moderation(cls, appointment: Appointment) -> None:
        """
        :raises: apps.appointments.exceptions.AppointmentApproveError
        """
        try:
            cls.check_valid_status(appointment, [cls.status_enum.REJECTED, cls.status_enum.PLANNED])
        except WrongStatusError as err:
            raise cls.base_error(title=err.title)


class AppointmentValidator(AppointmentModerationValidator):
    status_enum = AppointmentStatus
    wrong_status_error = AppointmentWrongStatusError

    @classmethod
    def required_data_filled(cls, data: CreateAppointmentByPatientDict) -> None:
        """
        :raise: AppointmentCreateError
        """
        service_id = data.get(SERVICE_ID)
        doctor_id = data.get(DOCTOR_ID)
        reason_text = data.get('reason_text')
        at_least_values = (service_id, doctor_id, reason_text)
        if not any(at_least_values):
            error_message = _('Должен быть указан или врач, или услуга, или текст жалобы')
            raise cls.create_error(title=error_message)

    @classmethod
    def validate_author_and_target_patients(cls, author_patient: Patient, target_patient_id: int):
        if not is_related_patients_enabled.is_enabled:
            err = AppointmentCreateError(
                code="not_valid_target_patient_id__wrong_settings",
                title=_('Param is not expected due to inner settings'),
            )
            logging.error(err)
            raise err

        if not PatientSelector.get_slave_related_patients(author_patient).exists():
            raise AppointmentCreateError(
                code="not_valid_target_patient_id__no_related_patients",
                title=_(
                    f"There are no related patient with this target_patient_id for current active patient"
                ),
            )
        # if not PatientSelector.get_or_none(target_patient_id):
        #     raise AppointmentCreateError(
        #         code="not_valid_target_patient_id", title=_('Patient does not exist')
        #     )

    @classmethod
    def validate_create_data(cls, data: CreateAppointmentByPatientDict, **kwargs) -> Dict:
        """
        Проверить входящие от фронтенда данные на создание Заявки
        :raises: apps.appointments.exceptions.AppointmentCreateError
        """
        print(f"AppointmentValidator.validate_create_data {data=}")

        cls.required_data_filled(data)
        cls._validate_start_end(data)

        # from main data
        doctor_id: Union[int, None] = data.get(DOCTOR_ID)
        target_patient_id: Union[int, None] = data.get(TARGET_PATIENT_ID)

        # from kwargs
        author_patient = kwargs.get(AUTHOR_PATIENT)
        if author_patient and target_patient_id:
            cls.validate_author_and_target_patients(
                author_patient=author_patient, target_patient_id=target_patient_id
            )

        if doctor_id:
            cls._is_data_valid_for_doctor(data)
            cls._check_time_free_for_doctor(data)
            if target_patient_id:
                cls._are_there_no_today_appointment_for_doctor(data, target_patient_id)
            elif author_patient:
                cls._are_there_no_today_appointment_for_doctor(data, author_patient)

        return data

    @classmethod
    def check_before_cancel_by_patient(cls, appointment: Appointment, patient: Patient) -> None:
        obj = appointment
        cls.check_valid_status(
            obj, expected_status=[cls.status_enum.ON_MODERATION, cls.status_enum.PLANNED]
        )
        cls._check_can_patient_update_appointment(obj, patient)


class TimeSlotValidator:
    @classmethod
    def doctor_has_intersected_slots(
        cls, doctor: Union[int, Doctor], start: datetime, exclude_ids: list = None
    ):
        intersected_slots = DoctorTimeSlots(doctor).all().intersects_with_start(start)
        if exclude_ids:
            intersected_slots = intersected_slots.exclude(id__in=exclude_ids)
        if intersected_slots.exists():
            return True
        return False
