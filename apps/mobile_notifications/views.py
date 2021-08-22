import json

import logging
from push_notifications.models import GCMDevice, APNSDevice
from rest_framework import viewsets, mixins, generics, status
from rest_framework.authentication import BasicAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from apps.core.permissions import IsSystemService
from apps.mobile_notifications import push
from apps.mobile_notifications.constants import FCM
from apps.mobile_notifications.serializers import (
    NotificationSerializer,
    PushEventSerializer,
    GCMDeviceSerializer,
    APNSDeviceSerializer,
    FCMDeviceSerializer,
)
from apps.mobile_notifications.signals import push_notification_event_received


class DeviceMinThrottle(UserRateThrottle):
    scope = 'mobile_notifications_device__min'


class DeviceMaxThrottle(UserRateThrottle):
    scope = 'mobile_notifications_device__max'


class BaseDeviceView(mixins.CreateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    throttle_classes = (
        DeviceMinThrottle,
        DeviceMaxThrottle,
    )
    lookup_field = 'registration_id'

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return self.model.objects.filter(user=self.request.user)
        return self.model.objects.none()

    def perform_create(self, serializer):
        logging.debug(f"{self.__class__.__name__} {serializer.data=}")
        serializer.save(user=self.request.user, active=True)

    def perform_destroy(self, instance):
        instance.user = None
        instance.save(update_fields=['user'])


class GCMDeviceView(BaseDeviceView):
    serializer_class = GCMDeviceSerializer
    model = GCMDevice


class FCMDeviceView(BaseDeviceView):
    serializer_class = FCMDeviceSerializer
    model = GCMDevice

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return self.model.objects.filter(user=self.request.user, cloud_message_type=FCM)
        return self.model.objects.none()

    def perform_create(self, serializer: FCMDeviceSerializer):
        logging.debug(f"{self.__class__.__name__}  {serializer.data=}")
        serializer.save(user=self.request.user, active=True, cloud_message_type=FCM)


class APNSDeviceView(BaseDeviceView):
    serializer_class = APNSDeviceSerializer
    model = APNSDevice


class NotificationView(generics.GenericAPIView):
    authentication_classes = (BasicAuthentication,)
    permission_classes = (
        IsAuthenticated,
        IsSystemService,
    )
    serializer_class = NotificationSerializer

    def post(self, request, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payload = json.loads(serializer.validated_data['message'])
        text_message = payload.pop('text')
        push.send_to_profile(
            message=text_message,
            subject='Новое событие',
            sender=request.user,
            sender_ip=request.META.get('REMOTE_HOST'),
            raise_error=False,
            profile=serializer.validated_data['profile'],
            payload=payload,
        )
        return Response(status=status.HTTP_201_CREATED)


class NotificationEventView(generics.GenericAPIView):
    def post(self, request, push_uuid, **kwargs):
        serializer = PushEventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        push_notification_event_received.send(
            push_uuid=push_uuid,
            event_type=serializer.validated_data['type'],
            event_labels=serializer.validated_data['event_labels'],
            sender=self.__class__,
        )

        return Response(status=status.HTTP_200_OK)
