# encoding=utf-8

from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from model_utils.models import TimeStampedModel

from apps.core.utils import generate_random_code


class SMSCode(TimeStampedModel):
    VALUE_LENGTH = 4

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, blank=True, null=True
    )
    phone_number = models.CharField(max_length=15, db_index=True)
    value = models.CharField(max_length=6, db_index=True)
    is_used = models.BooleanField(default=False, db_index=True)

    def save(self, *args, **kwargs):
        if not (self.pk and self.value):
            self.value = self.generate_value()
        super(SMSCode, self).save(*args, **kwargs)

    @classmethod
    def generate_value(cls, length=VALUE_LENGTH):
        return generate_random_code(length)

    @property
    def is_expired(self):
        created_after = timezone.now() - timedelta(seconds=settings.SMS_LOGIN_TIMEOUT)
        return self.created < created_after

    def __str__(self):
        return '{}: {}'.format(self.phone_number, self.value)

    class Meta:
        verbose_name = _('SMS-код')
        verbose_name_plural = _('SMS-коды')


class PhoneCode(models.Model):
    code = models.CharField(_('Код'), max_length=10, db_index=True, unique=True)
    provider = models.TextField(_('Сотовый оператор'), blank=True)
    digits_number = models.IntegerField(_('Знаков после кода'), null=True, blank=True)
    is_wired = models.BooleanField(_('Стационарный?'), default=False, db_index=True)

    def __str__(self):
        if self.is_wired:
            return '{} ({})'.format(7, self.code)
        return self.code

    class Meta:
        verbose_name = _('код телефона')
        verbose_name_plural = _('коды телефонов')
