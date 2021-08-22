from rest_framework import serializers

from apps.clinics.constants import ONLY_ROOT, PARENT_ID
from apps.clinics.serializer_validators import valid_mobile_app_section


class DoctorListFilterParamsSerializer(serializers.Serializer):
    subsidiary_ids = serializers.ListField(
        required=False, child=serializers.IntegerField(min_value=1)
    )
    service_ids = serializers.ListField(
        required=False, allow_empty=True, child=serializers.IntegerField(min_value=1)
    )
    without_fakes = serializers.BooleanField(required=False)


class ServiceListFilterParamsSerializer(serializers.Serializer):
    subsidiary_ids = serializers.ListField(
        required=False, child=serializers.IntegerField(min_value=1)
    )
    only_root = serializers.BooleanField(required=False)
    parent_id = serializers.IntegerField(required=False, min_value=1)
    mobile_app_section = serializers.CharField(
        required=False, max_length=100, min_length=5, validators=(valid_mobile_app_section,)
    )

    def validate(self, attrs: dict) -> dict:
        attrs = super().validate(attrs)
        if attrs.get(ONLY_ROOT) and attrs.get(PARENT_ID):
            raise serializers.ValidationError(
                f'only one of "{ONLY_ROOT}" OR "{PARENT_ID}" can be in params'
            )
        return attrs
