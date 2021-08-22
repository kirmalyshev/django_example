# encoding=utf-8
import logging
from typing import Union

from apps.core.backends import BaseNotifyBackend
from apps.core.decorators import mute_errors
from .constants import TARGET_SCREEN
from .models import PushLog

from .push import send_to_profile

import json  # dont delete

from apps.appointments.constants import (
    APPOINTMENT_REQUEST__REJECTED_BY_ADMIN,
    APPOINTMENT_REQUEST__APPROVED_BY_ADMIN,
    APPOINTMENT_CREATED_BY_ADMIN,
    REMIND_ABOUT_PLANNED_APPOINTMENT,
    APPOINTMENT_CANCELED_BY_ADMIN,
    APPOINTMENT__ASK_FOR_REVIEW,
)

TARGET_SCREEN_MAPPING = {
    # 'event_name': 'target_screen_name'
    APPOINTMENT_REQUEST__REJECTED_BY_ADMIN: "appointment_screen",
    APPOINTMENT_REQUEST__APPROVED_BY_ADMIN: "appointment_screen",
    APPOINTMENT_CREATED_BY_ADMIN: "appointment_screen",
    APPOINTMENT_CANCELED_BY_ADMIN: "appointment_screen",
    REMIND_ABOUT_PLANNED_APPOINTMENT: "appointment_screen",
    APPOINTMENT__ASK_FOR_REVIEW: "add_appointment_review_screen",
}


class PushBackend(BaseNotifyBackend):
    # @mute_errors
    def send(self, user, event_name, message, subject, *args, **kwargs):
        from .serializers import ProfileSerializer

        assert user, 'No user supplied'
        assert subject, 'No subject supplied'

        payload = {
            'action': event_name,
            'event_name': event_name,
            TARGET_SCREEN: TARGET_SCREEN_MAPPING.get(event_name, 'default'),
        }

        if 'from_profile' in kwargs:
            payload['from_user'] = ProfileSerializer(kwargs.pop('from_profile')).data
        payload.update(kwargs.get('extra_push_payload', {}))

        for key in ('thread_id', 'appointment_id'):
            if key in kwargs:
                payload[key] = kwargs.get(key)

        pushes = send_to_profile(
            profile=user.profile,
            message=message,
            subject=subject,
            raise_error=False,
            application_assignment=kwargs.pop('push_application_assignment', None),
            payload=payload,
        )
        if not kwargs.get('payload'):
            kwargs['payload'] = payload
        logging.info(pushes)
        self.log_message(text_message=message, user=user, event_name=event_name, **kwargs)
        self.log_push_message(user=user, event_name=event_name, message=message, payload=payload)

    def log_push_message(self, user, event_name, **kwargs):
        payload = kwargs.get('payload')
        data = {'message': kwargs.get('message'), 'payload': payload}
        appointment_id: Union[int, None] = payload and payload.get("appointment_id")
        PushLog.objects.create(
            user=user, event_name=event_name, data=data, appointment_id=appointment_id
        )
