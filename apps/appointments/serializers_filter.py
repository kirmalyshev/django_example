from rest_framework import serializers

from apps.appointments.constants import ONLY_FUTURE, ONLY_PAST, ONLY_ARCHIVED, ONLY_ACTIVE
from apps.appointments.serializer_validators import (
    valid_appointment_status_for_patient,
    is_not_past,
)


class BaseFilterParamsSerializer(serializers.Serializer):
    doctor_ids = serializers.ListField(
        required=False, max_length=20, child=serializers.IntegerField(min_value=1)
    )
    subsidiary_ids = serializers.ListField(
        required=False, max_length=20, child=serializers.IntegerField(min_value=1)
    )
    service_ids = serializers.ListField(
        required=False, max_length=20, allow_empty=True, child=serializers.IntegerField(min_value=1)
    )
    only_active = serializers.BooleanField(required=False, default=False)
    only_archived = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        if attrs[ONLY_ACTIVE] and attrs[ONLY_ARCHIVED]:
            raise serializers.ValidationError(
                f'only one of "{ONLY_ARCHIVED}" OR "{ONLY_ACTIVE}" can be in params'
            )
        return attrs


class AppointmentsFilterParamsSerializer(BaseFilterParamsSerializer):
    only_future = serializers.BooleanField(required=False, default=False)
    only_past = serializers.BooleanField(required=False, default=False)

    status_code = serializers.ListField(
        required=False,
        allow_empty=True,
        child=serializers.IntegerField(min_value=1),
        validators=[valid_appointment_status_for_patient],
    )
    related_patient_id = serializers.IntegerField(required=False, min_value=1, allow_null=False)

    def validate(self, attrs: dict) -> dict:
        attrs = super().validate(attrs)
        if attrs[ONLY_FUTURE] and attrs[ONLY_PAST]:
            raise serializers.ValidationError(
                f'only one of "{ONLY_FUTURE}" OR "{ONLY_PAST}" can be in params'
            )
        return attrs


class TimeSlotFilterSerializer(serializers.Serializer):
    start_date = serializers.DateField(required=False, validators=[is_not_past])
    doctor_id = serializers.IntegerField(required=False, min_value=1)


class AvailableTimeSlotsFilterSerializer(TimeSlotFilterSerializer):
    pass


class TimeSlotDateFilterSerializer(serializers.Serializer):
    doctor_id = serializers.IntegerField(required=False, min_value=1)
    subsidiary_id = serializers.IntegerField(required=False, min_value=1)
