import abc
from datetime import datetime, date, time
from typing import Union

from django.db.models import QuerySet, Q, Manager
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.appointments.constants import AppointmentStatus, AppointmentCreatedValues
from apps.clinics.models import Doctor, Subsidiary, Patient
from apps.clinics.utils import PatientUtils


class StartEndQuerySet(QuerySet):
    def past(self):
        """
        :rtype: StartEndQuerySet
        """
        now = timezone.now()
        return self.filter(Q(end__lt=now))

    def future(self):
        """
        :rtype: StartEndQuerySet
        """
        now = timezone.now()
        return self.filter(start__gte=now)

    def for_period(self, start: datetime, end: datetime):
        """
        :rtype: StartEndQuerySet
        """
        return self.filter(Q(start__range=(start, end)) | Q(end__range=(start, end)))

    def end_in_range(self, from_value: datetime, to_value: datetime):
        """
        :rtype: StartEndQuerySet
        """
        return self.filter(end__range=(from_value, to_value))

    def has_time_intersections(self, start: datetime, end: datetime) -> bool:
        """
        :rtype: BaseAppointmentQuerySet
        """
        return self.for_period(start, end).exists()

    def start_on_date(self, needed_date: date):
        """
        :rtype: StartEndQuerySet
        """
        return self.filter(
            **{
                'start__range': (
                    datetime.combine(needed_date, time.min),
                    datetime.combine(needed_date, time.max),
                )
            }
        )

    def start_before_day(self, needed_date: date):
        return self.filter(**{'start__lt': datetime.combine(needed_date, time.min),})

    def intersects_with_start(self, start: datetime):
        """
        :type start: datetime
        :rtype: StartEndQuerySet
        """
        q_filters = Q(start__lte=start, end__gte=start)
        return self.filter(q_filters)


class BaseAppointmentQuerySet(StartEndQuerySet):
    def for_doctor(self, doctor: Union[Doctor, int]):
        """
        :rtype: BaseAppointmentQuerySet
        """
        return self.filter(doctor=doctor).select_related(
            'patient', 'doctor', 'subsidiary', 'service'
        )

    def for_patient(self, patient: Patient):
        """
        :rtype: BaseAppointmentQuerySet
        """
        slave_patient_ids = PatientUtils.get_slave_patients_ids(patient)
        lookup_patient_ids = [patient.id] + slave_patient_ids
        return self.filter(patient_id__in=lookup_patient_ids).select_related(
            'patient', 'doctor', 'subsidiary', 'service'
        )

    @abc.abstractmethod
    def visible_by_patient(self):
        """
        :rtype: BaseAppointmentQuerySet
        """
        pass

    @abc.abstractmethod
    def visible_by_patient__active(self):
        """
        :rtype: BaseAppointmentQuerySet
        """
        pass

    @abc.abstractmethod
    def visible_by_patient__archived(self):
        """
        :rtype: BaseAppointmentQuerySet
        """
        # TODO rename to "archived"
        pass

    @abc.abstractmethod
    def not_processed_by_admin(self):
        """
        :rtype: BaseAppointmentQuerySet
        """
        pass


class AppointmentModerationQuerySet(BaseAppointmentQuerySet):
    status_enum = AppointmentStatus

    def on_moderation(self):
        """
        :rtype: AppointmentModerationQuerySet
        """
        return self.filter(status=self.status_enum.ON_MODERATION)

    def no_moderation_needed(self):
        """
        :rtype: AppointmentModerationQuerySet
        """
        return self.filter(~Q(status=self.status_enum.ON_MODERATION))

    def rejected(self):
        """
        :rtype: AppointmentModerationQuerySet
        """
        return self.filter(status=self.status_enum.REJECTED)

    def approved(self):
        """
        :rtype: AppointmentModerationQuerySet
        """
        return self.filter(status=self.status_enum.APPROVED)


class AppointmentQuerySet(AppointmentModerationQuerySet):
    def planned(self):
        """
        :rtype: AppointmentQuerySet
        """
        return self.filter(status=self.status_enum.PLANNED)

    def visible_by_patient(self):
        """
        :rtype: AppointmentQuerySet
        """
        return self.filter(status__in=self.status_enum.VISIBLE_FOR_PATIENT).without_hidden_doctors()

    def visible_by_patient__active(self):
        """
        :rtype: AppointmentQuerySet
        """
        return self.filter(
            status__in=AppointmentStatus.VISIBLE_BY_PATIENT__ACTIVE
        ).without_hidden_doctors()

    def visible_by_patient__archived(self):
        """
        :rtype: AppointmentQuerySet
        """
        return (
            self.filter(status__in=AppointmentStatus.VISIBLE_BY_PATIENT__ARCHIVED)
            .order_by(
                # '-start', '-modified',
                # '-modified', '-start',
                Coalesce('start', 'modified').desc()
            )
            .without_hidden_doctors()
        )

    def archived(self):
        """
        :rtype: AppointmentQuerySet
        """
        return (
            self.filter(status__in=AppointmentStatus.ARCHIVED)
            .without_hidden_doctors()
            .order_by('-start', '-created')
        )

    def not_canceled(self):
        """
        :rtype: AppointmentQuerySet
        """
        return self.filter(~Q(status__in=AppointmentStatus.CANCELED_VALUES))

    def with_active_users(self):
        """
        :rtype: AppointmentQuerySet
        """
        return self.filter(
            Q(patient__isnull=False)
            & Q(patient__profile__isnull=False)
            & ~Q(patient__profile__users=None)
        )

    def created_by_patient(self):
        """
        :rtype: AppointmentQuerySet
        """
        return self.filter(created_by_type=AppointmentCreatedValues.PATIENT)

    def without_hidden_doctors(self):
        """
        :rtype: AppointmentQuerySet
        """
        return self.exclude(doctor__is_totally_hidden=True)


class AppointmentManager(Manager.from_queryset(AppointmentQuerySet)):
    def get_queryset(self) -> AppointmentQuerySet:
        qs = super(AppointmentManager, self).get_queryset()
        return qs.select_related('patient', 'doctor', 'service', 'subsidiary')


class AppointmentOnModerationManager(AppointmentManager):
    def get_queryset(self) -> AppointmentQuerySet:
        qs = super(AppointmentOnModerationManager, self).get_queryset()
        return qs.on_moderation()


class PlannedAppointmentManager(AppointmentManager):
    def get_queryset(self) -> AppointmentQuerySet:
        qs = super(PlannedAppointmentManager, self).get_queryset()
        return qs.planned()


class ArchivedAppointmentManager(AppointmentManager):
    def get_queryset(self) -> AppointmentQuerySet:
        qs = super(ArchivedAppointmentManager, self).get_queryset()
        return qs.archived()


class TimeSlotManager(Manager):
    def get_queryset(self):
        return super().get_queryset().with_active_doctor()


class FutureTimeSlotManager(Manager):
    def get_queryset(self):
        return super().get_queryset().future()


class TimeSlotQuerySet(StartEndQuerySet):
    def with_active_doctor(self):
        """
        :rtype: TimeSlotQuerySet
        """
        return self.filter(doctor__is_removed=False).select_related('doctor',)

    def with_any_doctor(self):
        """
        :rtype: TimeSlotQuerySet
        """
        return self.filter(doctor__isnull=False).select_related('doctor',)

    def for_doctor(self, doctor: Union[Doctor, int]):
        """
        :rtype: TimeSlotQuerySet
        """
        return self.filter(doctor=doctor).select_related('doctor',)

    def for_subsidiary(self, subsidiary: Union[Subsidiary, int]):
        """
        :rtype: TimeSlotQuerySet
        """
        return self.filter(subsidiary=subsidiary).select_related('doctor', 'subsidiary')

    def free(self):
        """
        :rtype: TimeSlotQuerySet
        """
        return self.filter(is_available=True)

    def busy(self):
        """
        :rtype: TimeSlotQuerySet
        """
        return self.filter(is_available=False)
