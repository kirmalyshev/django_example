from django.conf import settings
from django.utils.translation import ugettext as _
from push_notifications.models import GCMDevice, APNSDevice
from rest_framework import serializers
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.logging.handlers import RequestHandler
from apps.profiles.models import Profile


class GCMDeviceSerializer(serializers.ModelSerializer):
    _valid_application_ids = (settings.GCM_DEFAULT_APPLICATION_ID,)
    registration_id = serializers.CharField()
    device_id = serializers.RegexField(required=False, regex='^[0-9a-fA-F]+$',)

    class Meta:
        model = GCMDevice
        fields = ('name', 'registration_id', 'application_id', 'device_id', 'cloud_message_type')
        extra_kwargs = {'application_id': {'default': settings.GCM_DEFAULT_APPLICATION_ID}}

    def save(self, **kwargs):
        validated_data = dict(list(self.validated_data.items()) + list(kwargs.items()))

        user_agent = RequestHandler().get_user_agent(request=self.context['request'])
        validated_data['name'] = f"{validated_data.get('name', '')} {user_agent}".strip()

        user = validated_data.get('user')
        if user and not user.is_authenticated:
            validated_data['user'] = None

        self.instance, _ = self.Meta.model.objects.update_or_create(
            registration_id=validated_data.get('registration_id'), defaults=validated_data
        )

        return self.instance

    def validate_application_id(self, value):
        if value not in self._valid_application_ids:
            raise DRFValidationError(_('Неверный идентификатор приложения'))

        return value


class APNSDeviceSerializer(GCMDeviceSerializer):
    _valid_application_ids = (settings.APNS_DEFAULT_APPLICATION_ID,)
    registration_id = serializers.RegexField(required=False, regex='^[0-9a-fA-F]{64}$')
    device_id = serializers.CharField(required=False)

    class Meta:
        model = APNSDevice
        fields = ('name', 'registration_id', 'application_id', 'device_id')
        extra_kwargs = {'application_id': {'default': settings.APNS_DEFAULT_APPLICATION_ID}}


class FCMDeviceSerializer(GCMDeviceSerializer):
    _valid_application_ids = (
        settings.GCM_DEFAULT_APPLICATION_ID,
        settings.APNS_DEFAULT_APPLICATION_ID,
    )


class NotificationSerializer(serializers.Serializer):
    profile = serializers.PrimaryKeyRelatedField(queryset=Profile.objects.filter(is_active=True))
    message = serializers.CharField(max_length=4000)


class ProfileSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    # name = serializers.CharField(source='chat_name')
    details = serializers.SerializerMethodField()
    type = serializers.IntegerField()

    def get_details(self, obj):
        return {'picture_url': obj.get_picture_url()}


class PushEventSerializer(serializers.Serializer):
    type = serializers.CharField()  # push event type (e.g. 'shown', 'clicked', etc)
    event_labels = serializers.ListField(allow_null=True)
