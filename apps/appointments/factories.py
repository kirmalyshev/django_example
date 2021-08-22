import abc
from datetime import datetime
from typing import Optional

import factory
from django.db.models.signals import post_save, pre_save
from django.utils import timezone
from factory import fuzzy
from factory.django import mute_signals

from apps.appointments.constants import AppointmentStatus
from apps.appointments.model_utils import (
    validate_appointment_start_end,
    validate_timeslot_start_end,
)
from apps.appointments.models import Appointment, TimeSlot
from apps.appointments.utils import TimeSlotUtils
from apps.appointments.validators import TimeSlotValidator
from apps.clinics.factories import PatientFactory, DoctorFactory, SubsidiaryFactory, ServiceFactory
from apps.clinics.models import Doctor


def _generate_valid_time_slot_start_end(initial: datetime, doctor: Doctor):
    for i in range(8):
        start = TimeSlotUtils.create_start(initial)
        end = TimeSlotUtils.create_end_from_start(start)

        if not TimeSlotValidator.doctor_has_intersected_slots(doctor, start):
            return start, end
    return None, None


@mute_signals(pre_save, post_save)
class StartEndFactory(factory.django.DjangoModelFactory):
    class Meta:
        abstract = True

    @classmethod
    @abc.abstractmethod
    def _validate_start_end(cls, start: datetime, end: datetime):
        pass

    @classmethod
    def _adjust_kwargs(
        cls,
        create_start_end: bool = True,
        initial_datetime: datetime = None,
        start: datetime = None,
        end: datetime = None,
        **kwargs,
    ):
        """Extension point for custom kwargs adjustment."""
        if create_start_end:
            if not initial_datetime:
                initial_datetime = timezone.now()
            if not start:
                start = TimeSlotUtils.create_start(initial_datetime)
            if not end:
                end = TimeSlotUtils.create_end_from_start(start)
            cls._validate_start_end(start, end)

            kwargs.update(
                {"start": start, "end": end,}
            )

        return kwargs


@mute_signals(pre_save, post_save)
class AppointmentFactory(StartEndFactory):
    patient = factory.SubFactory(PatientFactory)
    status = fuzzy.FuzzyChoice(AppointmentStatus.VALUES.keys())
    doctor = factory.SubFactory(DoctorFactory)
    service = factory.SubFactory(ServiceFactory)
    subsidiary = factory.SubFactory(SubsidiaryFactory)

    @classmethod
    def _validate_start_end(cls, start: datetime, end: datetime):
        return validate_appointment_start_end(start, end)

    class Meta:
        model = Appointment
        abstract = False


@mute_signals(pre_save, post_save)
class TimeSlotFactory(StartEndFactory):
    class Meta:
        model = TimeSlot
        abstract = False

    @classmethod
    def _validate_start_end(cls, start: datetime, end: datetime):
        return validate_timeslot_start_end(start, end)

    # doctor = factory.Iterator(Doctor.objects.all())
    subsidiary = factory.SubFactory(SubsidiaryFactory)

    @factory.post_generation
    def doctor(self, create: bool, extracted: Optional[Doctor], **kwargs) -> Optional[Doctor]:
        if not create:
            return

        if extracted:
            doctor = extracted
        else:
            if not Doctor.objects.exists():
                doctor = DoctorFactory()
            doctor: Doctor = Doctor.objects.latest('created')

        self.doctor = doctor
        self.save()
        return doctor
