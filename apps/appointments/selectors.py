import abc
from datetime import datetime
from typing import Union, Optional

from django.utils import timezone

from apps.appointments import models, managers
from apps.appointments.constants import (
    AppointmentStatus,
    ONLY_ACTIVE,
    ONLY_ARCHIVED,
    ONLY_PAST,
    ONLY_FUTURE,
    AUTHOR_PATIENT,
    DOCTOR,
    SUBSIDIARY,
    START,
)
from apps.appointments.managers import (
    AppointmentQuerySet,
    TimeSlotQuerySet,
)
from apps.clinics.constants import PATIENT
from apps.clinics.models import Patient
from apps.core.utils import today_range


class StartEndSelector:
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def all(self):
        return

    def has_for_future_period(self, start: datetime, end: datetime) -> bool:
        now = timezone.now()
        now = timezone.localtime(now)
        assert start >= now, 'start_time param must be in future'
        assert end >= now, 'end_time param must be in future'
        return self.all().future().has_time_intersections(start, end)


class BaseAppointmentsSelector(StartEndSelector):
    __metaclass__ = abc.ABCMeta
    model = models.BaseAppointment

    @abc.abstractmethod
    def all(self) -> managers.BaseAppointmentQuerySet:
        pass

    @abc.abstractmethod
    def visible_by_patient(self) -> managers.BaseAppointmentQuerySet:
        pass

    @abc.abstractmethod
    def visible_by_patient__active(self) -> managers.BaseAppointmentQuerySet:
        return self.all().visible_by_patient__active()

    @abc.abstractmethod
    def visible_by_patient__archived(self) -> managers.BaseAppointmentQuerySet:
        pass

    @classmethod
    def get_by_id(cls, obj_id: int) -> models.Appointment:
        qs = (
            cls.model.objects.all()
            .filter(id=obj_id)
            .select_related(
                DOCTOR,
                PATIENT,
                f'{PATIENT}__profile',
                AUTHOR_PATIENT,
                f"{AUTHOR_PATIENT}__profile",
            )
            .prefetch_related(f'{PATIENT}__profile__users', f"{AUTHOR_PATIENT}__profile__users")
        )
        return qs.get()

    @classmethod
    def get_or_none(cls, obj_id: int) -> Union[models.Appointment, None]:
        try:
            return cls.get_by_id(obj_id)
        except cls.model.DoesNotExist:
            return None


class AllAppointmentsSelector(BaseAppointmentsSelector):
    model = models.Appointment

    def all(self) -> managers.AppointmentQuerySet:
        return self.model.objects.all().order_by(START)

    def all_with_prefetched(self) -> managers.AppointmentQuerySet:
        return self.all().prefetch_related("time_slots").select_related(DOCTOR, PATIENT, SUBSIDIARY)

    def visible_by_patient(self) -> managers.AppointmentQuerySet:
        return self.all().visible_by_patient()

    def visible_by_patient__active(self) -> managers.AppointmentQuerySet:
        return self.all().visible_by_patient__active()

    def visible_by_patient__archived(self) -> managers.AppointmentQuerySet:
        return self.all().visible_by_patient__archived()

    def archived(self) -> managers.AppointmentQuerySet:
        return self.all().archived()

    def future_planned(self) -> managers.AppointmentQuerySet:
        return self.all().planned().future()

    @staticmethod
    def filter_by_params(queryset: AppointmentQuerySet, **kwargs) -> AppointmentQuerySet:
        subsidiary_ids = kwargs.get('subsidiary_ids', [])
        service_ids = kwargs.get('service_ids', [])
        doctor_ids = kwargs.get('doctor_ids', [])
        only_future = kwargs.get(ONLY_FUTURE)
        only_past = kwargs.get(ONLY_PAST)
        only_active = kwargs.get(ONLY_ACTIVE)
        only_archived = kwargs.get(ONLY_ARCHIVED)
        related_patient_id = kwargs.get("related_patient_id")
        statuses = kwargs.get('status_code', [])
        if only_future and only_past:
            raise ValueError(f'one of params [{ONLY_PAST}, {ONLY_FUTURE}] must be in kwargs')
        if only_active and only_archived:
            raise ValueError(f'one of params [{ONLY_ACTIVE}, {ONLY_ARCHIVED}] must be in kwargs')

        if only_future:
            queryset = queryset.future()
        elif only_past:
            queryset = queryset.past()

        if only_active:
            queryset = queryset.visible_by_patient__active()
        elif only_archived:
            queryset = queryset.visible_by_patient__archived()

        if service_ids:
            queryset = queryset.filter(service__id__in=service_ids)
        if doctor_ids:
            queryset = queryset.filter(doctor__id__in=doctor_ids)
        if subsidiary_ids:
            queryset = queryset.filter(subsidiary__id__in=subsidiary_ids)

        if statuses:
            valid_status_keys = AppointmentStatus.VALUES.keys()
            queryset = queryset.filter(status__in=[s for s in statuses if s in valid_status_keys])

        if related_patient_id:
            queryset = queryset.filter(patient_id=related_patient_id)

        return queryset


class DoctorAppointments(AllAppointmentsSelector):
    def __init__(self, doctor_id: int):
        self.doctor_id = doctor_id

    def all(self) -> managers.AppointmentQuerySet:
        return self.model.objects.for_doctor(self.doctor_id).order_by('start')


class PatientAppointments(AllAppointmentsSelector):
    """
    :type of patient: apps.clinics.models.Patient
    """

    def __init__(self, patient: Patient):
        self.patient = patient

    def all(self) -> managers.AppointmentQuerySet:
        return self.model.objects.for_patient(self.patient).order_by('start', 'modified')

    def visible_by_patient(self) -> managers.AppointmentQuerySet:
        qs = super(PatientAppointments, self).visible_by_patient()
        if not self.patient.is_confirmed:
            qs = qs.created_by_patient()
        return qs

    def visible_by_patient__active(self) -> managers.AppointmentQuerySet:
        qs = self.all().visible_by_patient__active()
        if not self.patient.is_confirmed:
            qs = qs.created_by_patient()
        return qs

    def visible_by_patient__archived(self) -> managers.AppointmentQuerySet:
        qs = self.all().visible_by_patient__archived()
        if not self.patient.is_confirmed:
            qs = qs.created_by_patient()
        return qs

    def on_moderation_created_today(
        self, patient: Optional[Patient] = None
    ) -> managers.AppointmentQuerySet:
        qs = (
            self.visible_by_patient__active()
            .created_by_patient()
            .filter(created__range=today_range(), status=AppointmentStatus.ON_MODERATION)
        )
        if patient:
            qs = qs.filter(patient=patient)
        return qs


class TimeSlots:
    model = models.TimeSlot

    def all(self) -> TimeSlotQuerySet:
        return self.model.objects.all()

    def free(self) -> TimeSlotQuerySet:
        return self.all().free()

    def busy(self) -> TimeSlotQuerySet:
        return self.all().busy()

    def all_for_period(self, start: datetime, end: datetime) -> TimeSlotQuerySet:
        return self.all().for_period(start, end)

    def free_for_period(self, start: datetime, end: datetime) -> TimeSlotQuerySet:
        return self.free().for_period(start, end)

    def busy_for_period(self, start: datetime, end: datetime) -> TimeSlotQuerySet:
        return self.busy().for_period(start, end)

    def free_future(self):
        return self.free().future()

    def free_past(self):
        return self.free().past()

    @classmethod
    def get_by_id(cls, obj_id: int) -> models.TimeSlot:
        qs = (
            cls.model.objects.filter(id=obj_id)
            .select_related('doctor',)
            .prefetch_related('appointments')
        )
        return qs.get()

    @staticmethod
    def filter_by_params(queryset: TimeSlotQuerySet, **kwargs) -> TimeSlotQuerySet:
        doctor_id = kwargs.get('doctor_id')
        subsidiary_id = kwargs.get('subsidiary_id')
        start_date = kwargs.get('start_date')

        if doctor_id:
            queryset = queryset.for_doctor(doctor_id)

        if subsidiary_id:
            queryset = queryset.for_subsidiary(subsidiary_id)

        if start_date:
            queryset = queryset.start_on_date(start_date)

        return queryset


class DoctorTimeSlots(TimeSlots):
    def __init__(self, doctor_id: int):
        self.doctor_id = doctor_id

    def all(self) -> TimeSlotQuerySet:
        return self.model.objects.for_doctor(self.doctor_id)
