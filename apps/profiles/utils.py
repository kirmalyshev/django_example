# coding: utf-8
from datetime import timedelta

from django.conf import settings
from django.utils import timezone


def lookup_user(email=None, phone=None):
    """
    Look up User either by a confirmed phone or email (not both!)
    Args:
        email: An e-mail as a string
        phone: A phone in the same format as it is stored in Contact (country code required, no plus sign)
    Returns:
        A django user object or None.
    """
    from apps.auth import utils as auth_utils

    if email:
        return auth_utils.get_user_by_email(email, raise_error=False)
    elif phone:
        return auth_utils.get_user_by_phone(phone, raise_error=False)
    return None


def phone_change_timeout():
    return timezone.now() + timedelta(seconds=settings.PRIMARY_PHONE_CONFIRM_AND_CHANGE_TIMEOUT)


def make_full_name(first_name=None, patronymic=None, last_name=None):
    parts = [
        last_name or '',
        first_name or '',
        patronymic or '',
    ]
    full_name = ' '.join(parts).strip()
    return full_name
