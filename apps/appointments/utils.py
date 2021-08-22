import random
from datetime import timedelta, datetime
from typing import Dict, Union, Set

import logging
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from apps.appointments import constants
from apps.appointments.constants import (
    APPOINTMENT_START,
    SUBSIDIARY_ADDRESS,
    DOCTOR_FULL_NAME,
    APPOINTMENT_STR_FOR_PATIENT,
    PATIENT_FULL_NAME,
    APPOINTMENT_REQUEST__REJECTED_BY_ADMIN,
    DefaultNotes,
)
from apps.appointments.models import Appointment
from apps.appointments.selectors import AllAppointmentsSelector
from apps.clinics.models import Patient
from apps.clinics.utils import PatientUtils
from apps.core.utils import human_dt


class StartEndUtils:
    max_minutes_range = int(constants.MAX_TIMESLOT_TIMEDELTA.total_seconds() / 60)
    minutes_range_start = 2  #

    @classmethod
    def generate_future_datetime(
        cls, initial_datetime: datetime, minutes_range: int = None
    ) -> datetime:
        if not minutes_range:
            minutes_range = cls.max_minutes_range

        minutes = random.choice(range(cls.minutes_range_start, minutes_range))
        return initial_datetime + timedelta(minutes=minutes)

    @classmethod
    def create_start(cls, initial_datetime: timezone.datetime = None) -> datetime:
        if not initial_datetime:
            initial_datetime = timezone.now()
        return cls.generate_future_datetime(initial_datetime)

    @classmethod
    def create_end_from_start(cls, start_datetime: datetime) -> datetime:
        return cls.generate_future_datetime(start_datetime)


class TimeSlotUtils(StartEndUtils):
    start_min_hour = 8
    start_max_hour = 19

    @classmethod
    def random_datetime_between(cls, start: datetime, end: datetime) -> datetime:
        delta = end - start
        seconds_delta = delta.total_seconds()
        random_seconds = random.randrange(seconds_delta)
        return start + timedelta(seconds=random_seconds)

    @classmethod
    def create_start(cls, initial: datetime = None) -> datetime:
        if not initial:
            initial = timezone.now()
        min = datetime(initial.year, initial.month, initial.day, cls.start_min_hour)
        max = datetime(initial.year, initial.month, initial.day, cls.start_max_hour)
        min = timezone.make_aware(min, initial.tzinfo)
        max = timezone.make_aware(max, initial.tzinfo)
        return cls.random_datetime_between(min, max)


class AppointmentUtils:
    @classmethod
    def get_user_ids_to_notify(cls, appointment: Union[Appointment, int]) -> Set[int]:
        """
        Из Записи на прием получает всех юзеров, которые могут быть заинтересованы в получении
        :param appointment_id:
        :return:
        """
        if isinstance(appointment, int):
            appointment = AllAppointmentsSelector.get_by_id(appointment)
        user_ids = []
        patient: Patient = appointment.patient
        profile = patient.profile
        if profile.user:
            user_ids.append(profile.user.id)
        master_user_ids = PatientUtils.get_master_user_ids(patient)
        user_ids += master_user_ids
        return set(user_ids)

    @classmethod
    def get_event_context_for_appointment_reminder(
        cls, appointment: Appointment, **kwargs
    ) -> Dict[str, str]:
        doctor_full_name = ''
        if appointment.doctor:
            doctor_full_name = appointment.doctor.short_full_name

        subsidiary_address = ''
        if appointment.subsidiary:
            subsidiary_address = appointment.subsidiary.short_address

        context = {
            APPOINTMENT_STR_FOR_PATIENT: appointment.str_for_patient,
            APPOINTMENT_START: appointment.human_start_tz,
            DOCTOR_FULL_NAME: doctor_full_name,
            SUBSIDIARY_ADDRESS: subsidiary_address,
        }
        if kwargs.get('with_patient_full_name'):
            context[PATIENT_FULL_NAME] = f"Пациент: {appointment.patient.full_name}"

        event_name = kwargs.get('event_name', '')
        if event_name == APPOINTMENT_REQUEST__REJECTED_BY_ADMIN:
            if doctor_full_name:
                request_info = _(f"к доктору {doctor_full_name}")
            elif context[APPOINTMENT_START]:
                request_info = _(f"на {context[APPOINTMENT_START]}")
            elif appointment.service_id:
                request_info = _(f"на услугу {appointment.service.title}")
            else:
                request_info = _(f"от {human_dt(appointment.created)}")

            context['appointment_request_info'] = request_info
        return context
