# encoding=utf-8

from __future__ import print_function
from __future__ import unicode_literals

import string

from django.core.validators import RegexValidator
from django.utils.translation import ugettext_lazy as _, ugettext as _
from phonenumber_field.validators import validate_international_phonenumber
from rest_framework.exceptions import ValidationError

from apps.core.utils import validate_chars

validate_phone_number_naive = RegexValidator(r'^\d{10,}$', message=_('Неверный формат номера'))
validate_phone_number_naive.__doc__ = """
This is for cases when we are looking up the value in the database anyway
and thus don't need rigorous validation
"""


def validate_phone_number(value: str, add_plus_sign=True):
    if add_plus_sign and not value.startswith('+'):
        value = '+' + value
    return validate_international_phonenumber(value)


def validate_phone__if_value_contains_only_digits(value: str) -> None:
    """
    Check for wrong chars. Only digits allowed.
    :raises: rest_framework.exceptions.ValidationError
    """
    if not validate_chars(value, string.digits):
        raise ValidationError(_('Недопустимые символы в номере телефона'))


def validate_phone__if_russian_country_code(value: str) -> None:
    """
    Check for wrong country code.
    :raises: rest_framework.exceptions.ValidationError
    """
    valid_codes = ['7', '8']
    if value[0] not in valid_codes:
        raise ValidationError(_(f'Неверный код страны. Должен быть один из {valid_codes}'))
