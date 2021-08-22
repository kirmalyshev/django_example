import calendar
from datetime import datetime
from typing import Optional

from ckeditor.fields import RichTextField
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.fields.json import JSONField
from django.template.defaultfilters import date as template_date
from django.utils import translation, timezone
from django.utils.functional import cached_property
from django.utils.timezone import get_default_timezone
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel, TimeFramedModel

from apps.appointments import managers
from apps.appointments.constants import AppointmentStatus, AppointmentCreatedValues, DefaultNotes
from apps.appointments.model_utils import (
    validate_appointment_start_end,
    validate_timeslot_start_end,
)
from apps.clinics.constants import DOCTOR_STR, SUBSIDIARY_STR
from apps.core.models import TimeStampIndexedModel
from apps.core.utils import dt_no_seconds, datetime_tz_formatted


class StartEndModelMixin(TimeFramedModel):
    start = models.DateTimeField(_('Дата/время начала'), blank=True, null=True,)
    end = models.DateTimeField(_('Дата/время конца'), blank=True, null=True)
    duration = models.DurationField(_('Длительность'), blank=True, null=True)

    class Meta:
        abstract = True

    @property
    def duration_in_minutes(self):
        if not self.duration:
            return
        return self.duration.seconds / 60

    def save(self, **kwargs):
        if self.start and self.end:
            self.duration = self.end - self.start
        super(StartEndModelMixin, self).save(**kwargs)

    @property
    def start_tz(self) -> Optional[datetime]:
        if not self.start:
            return
        return self.start.astimezone(get_default_timezone())

    @property
    def start_tz_no_seconds(self) -> Optional[datetime]:
        if not self.start_tz:
            return
        return dt_no_seconds(self.start_tz)

    @property
    def end_tz(self) -> Optional[datetime]:
        if not self.end:
            return
        return self.end.astimezone(get_default_timezone())

    @property
    def end_tz_no_seconds(self) -> Optional[datetime]:
        if not self.end_tz:
            return
        return dt_no_seconds(self.end_tz)

    @property
    def start_date_tz_formatted(self) -> str:
        start = self.start_tz_no_seconds
        if not start:
            return ""
        return datetime_tz_formatted(start)

        start_date = start.date() if start else ""
        start_date = f"{start_date:%d.%m.%Y}" if start_date else ""
        return start_date

    @property
    def start_date_tz_formatted__short(self) -> str:
        start = self.start_tz_no_seconds
        if not start:
            return ""
        start_date = start.date() if start else ""
        start_date = f"{start_date:%d.%m}" if start_date else ""
        return start_date

    @property
    def start_time_tz_formatted(self) -> str:
        start = self.start_tz_no_seconds
        if not start:
            return ""
        start_time = start.time() if start else ""
        start_time = f"{start_time:%H:%M}" if start_time else ""
        return start_time

    @property
    def human_start_tz(self) -> str:
        start_date = self.start_date_tz_formatted
        start_time = self.start_time_tz_formatted
        at_start_time = f" в {start_time}" if start_time else ""
        return f"{start_date}{at_start_time}"

    @property
    def human_start_datetime(self) -> str:
        start = self.start_tz_no_seconds
        if not start:
            return ""
        return template_date(start, settings.TIME_DATE_FORMATTER)

    @property
    def human_start_date(self) -> str:
        start = self.start_tz_no_seconds
        if not start:
            return ""
        return template_date(start, settings.DATE_FORMATTER_SHORT)

    @property
    def human_weekday(self) -> str:
        start = self.start_tz_no_seconds
        if not start:
            return ""
        weekday: int = start.weekday()
        translation.activate(settings.LANGUAGE_CODE)
        ru_weekday = _(calendar.day_name[weekday])
        return ru_weekday.lower()


class BaseAppointment(StartEndModelMixin, TimeStampIndexedModel):
    patient = models.ForeignKey(
        'clinics.Patient', verbose_name=_('пациент'), on_delete=models.DO_NOTHING, db_index=True
    )
    doctor = models.ForeignKey(
        'clinics.Doctor',
        verbose_name=DOCTOR_STR,
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
        db_index=True,
    )
    service = models.ForeignKey(
        'clinics.Service',
        verbose_name=_('услуга'),
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
        db_index=True,
    )
    subsidiary = models.ForeignKey(
        'clinics.Subsidiary',
        verbose_name=_('филиал'),
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
        db_index=True,
    )

    integration_data = JSONField(
        verbose_name=_('Данные об интеграции'), encoder=DjangoJSONEncoder, default=dict, blank=True,
    )

    additional_notes = RichTextField(
        _('пометки'),
        help_text=_(
            'дополнительная информация, которую нужно знать пациенту о приеме. '
            'Указывать в виде маркированного списка'
        ),
        null=True,
        blank=True,
    )
    is_for_whole_day = models.BooleanField(_(f"{DefaultNotes.DURING_ALL_DAY}?"), default=False,)

    objects = managers.BaseAppointmentQuerySet.as_manager()

    @property
    def human_start_time(self) -> str:
        if self.is_for_whole_day:
            start_time = DefaultNotes.DURING_ALL_DAY
        else:
            start_time = self.start_time_tz_formatted
        return start_time

    @property
    def human_start_tz(self) -> str:
        start_date = self.start_date_tz_formatted
        start_time = self.human_start_time
        weekday = self.human_weekday

        whole_weekday = f", {weekday}," if weekday else ""

        if f"{DefaultNotes.DURING_ALL_DAY}" not in start_time:
            at_start_time = f" в {start_time}" if start_time else ""
        else:
            at_start_time = f" {start_time}" if start_time else ""

        return f"{start_date}{whole_weekday}{at_start_time}"

    def clean(self):
        super(StartEndModelMixin, self).clean()
        if self.start and self.end:
            validate_appointment_start_end(self.start, self.end)

    class Meta:
        unique_together = ('patient', 'doctor', 'subsidiary', 'start', 'end')
        abstract = True


class AppointmentStatusMixin(models.Model):
    status_enum = AppointmentStatus

    class Meta:
        abstract = True

    # region moderation
    @property
    def is_on_moderation(self):
        return self.status == self.status_enum.ON_MODERATION

    def mark_on_moderation(self, save=True):
        if self.is_on_moderation:
            return
        self.status = self.status_enum.ON_MODERATION
        if save:
            self.save()

    @property
    def is_rejected(self):
        return self.status == self.status_enum.REJECTED

    def mark_rejected(self, save=True):
        if self.is_rejected:
            return
        self.status = self.status_enum.REJECTED
        if save:
            self.save()

    # endregion

    @property
    def is_planned(self):
        return self.status == self.status_enum.PLANNED

    def mark_planned(self, save=True):
        self.status = self.status_enum.PLANNED
        if save:
            self.save()

    @property
    def is_hidden(self):
        return self.status == self.status_enum.HIDDEN

    def mark_hidden(self, save=True):
        self.status = self.status_enum.HIDDEN
        if save:
            self.save()

    @property
    def is_visible_for_patient(self):
        return self.status in self.status_enum.VISIBLE_FOR_PATIENT

    @property
    def is_cancel_requested_by_patient(self):
        return self.status == self.status_enum.CANCEL_REQUEST_BY_PATIENT

    def mark_cancel_request_by_patient(self, save=True):
        self.status = self.status_enum.CANCEL_REQUEST_BY_PATIENT
        if save:
            self.save()

    @property
    def is_canceled_by_patient(self):
        return self.status == self.status_enum.CANCELED_BY_PATIENT

    def mark_canceled_by_patient(self, save=True):
        self.status = self.status_enum.CANCELED_BY_PATIENT
        if save:
            self.save()

    def mark_canceled_by_moderator(self, save=True):
        self.status = self.status_enum.CANCELED_BY_MODERATOR
        if save:
            self.save()

    @property
    def is_payment_enabled(self):
        return self.status == self.status_enum.AWAITING_PAYMENT

    @property
    def is_cancel_by_patient_available(self) -> bool:
        return self.status in self.status_enum.AVAILABLE_TO_CANCEL_BY_PATIENT

    @property
    def is_finished(self):
        return self.status == self.status_enum.FINISHED

    def mark_finished(self, save=True):
        self.status = self.status_enum.FINISHED
        if save:
            self.save()

    @property
    def is_archived(self):
        return self.status in self.status_enum.ARCHIVED


class Appointment(BaseAppointment, AppointmentStatusMixin):
    """
    Запись на прием.

    Может создаваться
    1. В системе клиники, и подтягигиваться к нам через шлюз интеграции
    2. Приходить от пациента
    """

    status = models.PositiveSmallIntegerField(
        verbose_name=_('статус'),
        choices=AppointmentStatusMixin.status_enum.CHOICES,
        db_index=True,
        null=True,
    )
    reason_text = models.TextField(_('жалоба пациента'), null=True, blank=True)
    price = models.DecimalField(
        _('стоимость'),
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0)],
        decimal_places=2,
        max_digits=8,
    )
    created_by_type = models.CharField(
        _("Кем создана запись?"),
        choices=AppointmentCreatedValues.CHOICES,
        null=True,
        blank=True,
        max_length=100,
    )
    author_patient = models.ForeignKey(
        'clinics.Patient',
        verbose_name=_('пациент-создатель'),
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
        db_index=True,
        related_name='created_appointments',
    )

    class Meta(BaseAppointment.Meta):
        verbose_name = _('Запись на приём')
        verbose_name_plural = _('Записи на приём')
        unique_together = ('patient', 'doctor', 'service', 'subsidiary', 'start', 'end')
        abstract = False

    def __str__(self):
        return self.short_str

    @property
    def short_str(self) -> str:
        doctor = (self.doctor_id and self.doctor) or ''
        to_doctor = f"{(', врач ' + doctor.short_full_name) if doctor else ''}"
        value = f"Запись на прием {self.id}: {self.patient}{to_doctor}"
        start_date = self.start_date_tz_formatted
        start_time = self.start_time_tz_formatted
        if start_time:
            value += f", {start_date} {start_time}"
        return value

    @property
    def str_for_patient(self) -> str:
        doctor = (self.doctor_id and self.doctor) or ''
        to_doctor = f"{(', врач ' + doctor.short_full_name) if doctor else ''}"
        return f"{self.human_start_tz}{to_doctor}"

    @cached_property
    def has_timeslots(self) -> bool:
        return self.time_slots.exists()

    @cached_property
    def has_reviews(self) -> bool:
        return self.review_set.exists()

    objects = managers.AppointmentManager()

    def clean(self):
        super(Appointment, self).clean()
        at_least_values = (self.service_id, self.doctor_id, self.reason_text)
        if not any(at_least_values):
            error_message = _('Должен быть указан врач, или услуга, или текст жалобы')
            raise ValidationError(error_message)

    def save(self, **kwargs):
        self.full_clean()
        super(Appointment, self).save(**kwargs)

    @property
    def is_created_by_patient(self):
        return self.created_by_type == AppointmentCreatedValues.PATIENT


class AppointmentOnModeration(Appointment):
    class Meta:
        proxy = True
        verbose_name = _('Необработанная запись')
        verbose_name_plural = _(' Необработанные записи')

    objects = managers.AppointmentOnModerationManager()


class PlannedAppointment(Appointment):
    class Meta:
        proxy = True
        verbose_name = _('Запланированная запись')
        verbose_name_plural = _('Запланированные записи')

    objects = managers.PlannedAppointmentManager()


class ArchivedAppointment(Appointment):
    class Meta:
        proxy = True
        verbose_name = _('Архивная запись')
        verbose_name_plural = _('Архивные записи')

    objects = managers.ArchivedAppointmentManager()


class TimeSlotToAppointment(models.Model):
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE)
    time_slot = models.ForeignKey('TimeSlot', on_delete=models.PROTECT)

    class Meta:
        verbose_name = _('связь Записи на прием с таймслотами')
        verbose_name_plural = _('связи Записи на прием с таймслотами')


class TimeSlot(StartEndModelMixin, TimeStampedModel):
    appointments = models.ManyToManyField(
        Appointment,
        through=TimeSlotToAppointment,
        verbose_name=_('Записи на прием'),
        blank=True,
        related_name='time_slots',
    )

    doctor = models.ForeignKey(
        'clinics.Doctor',
        verbose_name=DOCTOR_STR,
        on_delete=models.DO_NOTHING,
        db_index=True,
        null=True,
        blank=True,
    )
    subsidiary = models.ForeignKey(
        'clinics.Subsidiary',
        verbose_name=SUBSIDIARY_STR,
        on_delete=models.CASCADE,
        db_index=True,
        null=True,
        blank=True,
    )
    is_available = models.BooleanField(
        verbose_name=_("доступна ли запись в этот слот"), default=True
    )
    integration_data = JSONField(
        verbose_name=_('Данные об интеграции'), encoder=DjangoJSONEncoder, default=dict, blank=True,
    )

    objects = managers.TimeSlotManager.from_queryset(managers.TimeSlotQuerySet)()
    all_objects = managers.Manager.from_queryset(managers.TimeSlotQuerySet)()

    class Meta:
        verbose_name = _('Талон')
        verbose_name_plural = _('Талоны')
        ordering = ('start', 'duration')

    @property
    def short_str(self) -> str:
        start_date = self.start_date_tz_formatted
        start_time = self.start_time_tz_formatted
        end_time = f"{self.end_tz_no_seconds.time():%H:%M}" if self.end_tz_no_seconds else ''
        value = f"{start_date} {start_time}{'-' + end_time if end_time else ''}"
        if self.doctor_id:
            value += f", {self.doctor.short_full_name or ''}"
        return value

    def __str__(self):
        return f"{self.id}: {self.short_str}"

    def clean(self):
        super(StartEndModelMixin, self).clean()
        if self.start and self.end:
            validate_timeslot_start_end(self.start, self.end)

    @cached_property
    def first_appointment(self) -> Optional[Appointment]:
        return self.appointments.all().first()

    def mark_available(self, save=True):
        self.is_available = True
        if save:
            self.save()

    def mark_unavailable(self, save=True):
        self.is_available = False
        if save:
            self.save()


class FutureTimeSlot(TimeSlot):
    class Meta:
        proxy = True
        verbose_name = _('Талон в будущем')
        verbose_name_plural = _('Талоны в будущем')

    objects = managers.FutureTimeSlotManager.from_queryset(managers.TimeSlotQuerySet)()


class AppointmentResult(TimeStampIndexedModel):
    appointment = models.OneToOneField(Appointment, on_delete=models.PROTECT, related_name='result')
    complaints = models.TextField(verbose_name=_("жалобы"), null=True, blank=True)
    diagnosis = models.TextField(verbose_name=_("диагноз"), null=True, blank=True)
    recommendations = models.TextField(verbose_name=_("рекомендации"), null=True, blank=True)

    class Meta:
        verbose_name = _("результат приема")
        verbose_name_plural = _("результаты приема")
