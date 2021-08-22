from datetime import timedelta

import logging
from typing import Type

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.module_loading import import_string
from django.utils.translation import ugettext as __

from apps.auth.utils import get_user_by_phone
from apps.sms.models import SMSCode
from .backends import BaseBackend
from ..notify.constants import SMS
from ..tmp_tools.constants import PHONE_FOR_APPLE_STORE_TESTERS, CODE_FOR_APPLE_STORE_TESTERS


class SMSCodeHandler:
    """
    Handle SMS code verification for authentication
    and phone confirmation purposes.
    """

    def __init__(self, phone, **kwargs):
        self._phone = phone
        self._user = kwargs.get('user')

    @property
    def phone(self):
        phone = self._phone
        return phone.lstrip('+')

    @property
    def user(self):
        if self._user:
            user = self._user
        else:
            user = get_user_by_phone(self.phone)
        return user

    def send_code(self, **kwargs):
        message = kwargs.get('message')
        empty_user = kwargs.get('empty_user', False)

        if not empty_user:
            params = {'user': self.user}
        else:
            params = {'user': None}

        if self.phone == PHONE_FOR_APPLE_STORE_TESTERS:
            qs = SMSCode.objects.filter(phone_number=self.phone)
            qs.update(
                is_used=False,
                created=timezone.now() - timedelta(seconds=settings.SMS_LOGIN_TIMEOUT / 3),
            )
            code = qs.first()
            if not code:
                code = SMSCode.objects.get_or_create(
                    phone_number=self.phone, value=CODE_FOR_APPLE_STORE_TESTERS, **params
                )
        else:
            try:
                code = SMSCode.objects.get(phone_number=self.phone, is_used=False, **params)
                if code.is_expired:
                    code.delete()
                    code = SMSCode.objects.create(phone_number=self.phone, **params)
            except SMSCode.MultipleObjectsReturned:
                SMSCode.objects.filter(phone_number=self.phone, is_used=False, **params).delete()
                code = SMSCode.objects.create(phone_number=self.phone, **params)
            except SMSCode.DoesNotExist:
                code = SMSCode.objects.create(phone_number=self.phone, **params)

        if not message:
            try:
                from apps.notify.models import Template

                template = Template.objects.get(event__name='authorization_code', channel__name=SMS)
                message = template.message.replace('{{ authorization_code }}', code.value)
            except Template.DoesNotExist:
                message = settings.SMS_DEFAULT_TEMPLATE.format(code.value)
        send(code.phone_number, message)
        return code

    def verify_code(self, code, empty_user=False):
        if not empty_user:
            params = {'user': self.user}
        else:
            params = {'user': None}

        try:
            created_after = timezone.now() - timedelta(seconds=settings.SMS_LOGIN_TIMEOUT)
            code = SMSCode.objects.get(
                phone_number=self.phone,
                value=code,
                is_used=False,
                created__gte=created_after,
                **params,
            )
        except SMSCode.DoesNotExist:
            raise ValidationError(__('Неверный код'))

        code.is_used = True
        code.save()

        if not empty_user and self.user:
            self.user.contacts.filter(type='phone', value=self.phone).update(is_confirmed=True)
        return True


def get_backend(backend_path=None, **kwargs):
    if not backend_path:
        backend_path = settings.SMS_BACKEND
    try:
        klass = import_string(backend_path)
    except ImportError as err:
        raise ImproperlyConfigured(
            ('Error importing SMS backend module %s: "%s"' % (backend_path, err))
        )

    params = {}
    params.update(settings.SMS_BACKEND_PARAMS)
    params.update(kwargs)
    return klass(**params)


def send(to, body):
    sms_backend: BaseBackend = get_backend()
    sms_backend.send(to, body)
