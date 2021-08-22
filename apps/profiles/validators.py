from datetime import date

from dateutil.utils import today
from django.core.validators import RegexValidator
from django.utils.translation import ugettext_lazy as _

from rest_framework.exceptions import ValidationError as DRFValidationError

phone_validator = RegexValidator(regex=r'\d{8,11}', message=_('Неправильный формат телефона'))
wired_phone_validator = RegexValidator(regex=r'\d{5,15}', message=_('Неправильный формат телефона'))


def validate_birth_date(value: date):
    if value > today().date():
        raise DRFValidationError(_("Дата рождения не может быть в будущем"))
    return value
