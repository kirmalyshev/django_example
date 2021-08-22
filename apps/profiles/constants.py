# coding: utf-8
from typing import Final

from django.utils.translation import ugettext as _

ADMIN_EMAIL = 'admin@django_example.com'
ADMIN_USERNAME = 'admin@django_example.com'
DEFAULT_PASSWORD = '123321'


# region String Constants
PROFILE_ID: Final = "profile_id"
FULL_NAME: Final = "full_name"
LAST_NAME: Final = "last_name"
FIRST_NAME: Final = "first_name"
PATRONYMIC: Final = "patronymic"
BIRTH_DATE = "birth_date"
GENDER: Final = "gender"
RELATION_ID: Final = "relation_id"
RELATION_TYPE: Final = "relation_type"


ADD_PRIMARY_PHONE = 'add_primary_phone'
ADD_PRIMARY_EMAIL = 'add_primary_email'


# endregion


class ContactType:
    PHONE = 'phone'
    EMAIL = 'email'

    TYPES = [PHONE, EMAIL]

    CHOICES = ((PHONE, _('телефон')), (EMAIL, _('e-mail')))


class ProfileType:
    SYSTEM = 0
    DOCTOR = 1
    CLINIC_STAFF = 2
    PATIENT = 3

    PROFILE_TYPES = (
        (SYSTEM, _('системный')),
        (DOCTOR, _('доктор')),
        (CLINIC_STAFF, _('персонал клиники')),
        (PATIENT, _('пациент')),
    )


class ProfileGroupType:
    SYSTEM = 'system'
    FAMILY = 'family'
    OTHER = 'other'

    VALUES = {
        SYSTEM: _('системный'),
        FAMILY: _('семья'),
        OTHER: _('другое'),
    }
    CHOICES = VALUES.items()


class RelationType:
    CHILD = 'child'
    PARENT = 'parent'
    SIBLING = 'sibling'
    OTHER = 'other'
    PARTNER = 'partner'

    VALUES = {
        CHILD: _('ребенок'),
        PARTNER: _('муж/жена'),
        PARENT: _('родитель'),
        SIBLING: _('брат/сестра'),
        OTHER: _('другое'),
    }
    CHOICES = VALUES.items()
    UI_CHOICES = tuple(CHOICES)
    # TODO добавить точку для фронта, чтоб можно было на них ориентироваться на клиенте


class Gender:
    NOT_SET = 'no'
    MAN = 'man'
    WOMAN = 'woman'

    CHOICES = {
        NOT_SET: _('не указан'),
        MAN: _('мужской'),
        WOMAN: ('женский'),
    }
    MODEL_CHOICES = tuple((key, value) for key, value in CHOICES.items())

    UI_CHOICES = ((MAN, _('мужской')), (WOMAN, _('женский')))
