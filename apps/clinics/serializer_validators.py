from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers

from apps.clinics.constants import MobileAppSections


def valid_mobile_app_section(mobile_app_section: str):
    valid_values = MobileAppSections.VALUES
    if mobile_app_section not in valid_values:
        raise serializers.ValidationError(
            _(f'Invalid mobile_app_section value. Available values: {valid_values}')
        )
