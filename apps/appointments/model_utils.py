from datetime import datetime, timedelta

from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import ugettext_lazy as _

from apps.appointments import constants


def _validate_start_end(start: datetime, end: datetime, min_delta: timedelta, max_delta: timedelta):
    """
    :raises: django.core.exceptions.ValidationError
    """
    if start > end:
        raise DjangoValidationError(
            _(f"Время начала должно быть меньше времени окончания. start: {start}; end: {end}")
        )

    delta = end - start
    # if delta <= min_delta:
    #     raise DjangoValidationError(_(f'Длительность не может быть меньше/равной чем {min_delta}'))

    if delta > max_delta:
        raise DjangoValidationError(_(f'Длительность не может быть больше чем {max_delta}'))


def validate_appointment_start_end(start: datetime, end: datetime) -> None:
    """
    :type start: datetime.datetime
    :type end: datetime.datetime
    :raises: django.core.exceptions.ValidationError
    """
    return _validate_start_end(
        start, end, constants.MIN_APPOINTMENT_TIMEDELTA, constants.MAX_APPOINTMENT_TIMEDELTA
    )


def validate_timeslot_start_end(start: datetime, end: datetime) -> None:
    """
    :type start: datetime.datetime
    :type end: datetime.datetime
    :raises: django.core.exceptions.ValidationError
    """
    return _validate_start_end(
        start, end, constants.MIN_TIMESLOT_TIMEDELTA, constants.MAX_TIMESLOT_TIMEDELTA
    )
