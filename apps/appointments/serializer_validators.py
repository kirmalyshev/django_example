from datetime import datetime
from typing import List

from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from apps.appointments.constants import AppointmentStatus


def valid_appointment_status_for_patient(value: List[int]):
    valid_values = set(AppointmentStatus.VISIBLE_FOR_PATIENT)
    if not set(value).issubset(valid_values):
        raise serializers.ValidationError(
            _(f'Invalid status value. Available values: {valid_values}')
        )


def is_not_past(value: datetime.date):
    today = timezone.now().date()
    if value < today:
        raise serializers.ValidationError(_(f"Invalid value. Must be today or future date"))
