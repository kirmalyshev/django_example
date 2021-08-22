from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from apps.core.models import TimeStampIndexedModel, DisplayableModel
from apps.reviews import managers
from apps.reviews.constants import ReviewStatus


class ReviewGrade:
    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5

    ITEMS = {
        ONE: _('1'),
        TWO: _('2'),
        THREE: _('3'),
        FOUR: _('4'),
        FIVE: _('5'),
    }
    CHOICES = ITEMS.items()


class ReviewStatusMixin(models.Model):
    status_enum = ReviewStatus

    class Meta:
        abstract = True

    # region moderation
    @property
    def is_on_moderation(self):
        return self.status == self.status_enum.ON_MODERATION

    def mark_on_moderation(self, save=True):
        self.status = self.status_enum.ON_MODERATION
        if save:
            self.save()

    @property
    def is_new(self):
        return self.status == self.status_enum.NEW

    def mark_new(self):
        self.status = self.status_enum.NEW
        self.save()

    @property
    def is_processed(self):
        return self.status == self.status_enum.PROCESSED

    def mark_processed(self):
        self.status = self.status_enum.PROCESSED
        self.save()

    # endregion


class Review(TimeStampIndexedModel, DisplayableModel, ReviewStatusMixin):
    is_displayed = models.BooleanField(verbose_name=_('отображается?'), default=False)

    grade = models.PositiveSmallIntegerField(
        _('оценка'), choices=ReviewGrade.CHOICES, db_index=True, null=True, blank=True
    )
    text = models.TextField(_('Текст'))
    # whats_good = models.TextField(_('что понравилось'), blank=True)
    # whats_bad = models.TextField(_('что не понравилось'), blank=True)

    appointment = models.ForeignKey(
        'appointments.Appointment',
        verbose_name=_('запись на прием'),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    author_patient = models.ForeignKey(
        'clinics.Patient', verbose_name=_('пациент - автор отзыва'), on_delete=models.PROTECT
    )
    doctor = models.ForeignKey('clinics.Doctor', verbose_name=_('врач'), on_delete=models.PROTECT)
    status = models.PositiveSmallIntegerField(
        verbose_name=_('статус'),
        choices=ReviewStatusMixin.status_enum.CHOICES,
        db_index=True,
        null=True,
        blank=True,
        default=ReviewStatusMixin.status_enum.NEW,
    )

    class Meta:
        verbose_name = _('Отзыв')
        verbose_name_plural = _('Отзывы')

    objects = managers.ReviewManager()

    @cached_property
    def short_str(self):
        return f"Оценка {self.grade}, author_patient_id={self.author_patient_id}, doctor_id={self.doctor_id}"

    @cached_property
    def short_text(self):
        max_len = 20
        if len(self.text) < max_len:
            return self.text
        return self.text[: max_len - 2] + '..'

    def __str__(self):
        return self.short_str
