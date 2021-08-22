import logging

from push_notifications.apns import APNSServerError
from push_notifications.gcm import GCMError
from push_notifications.models import APNSDevice, GCMDevice

from apps.core.utils import generate_uuid
from apps.logging.utils import RecordLog
from apps.mobile_notifications.constants import PAYLOAD, EXTRA, BODY, TITLE, TARGET_SCREEN
from apps.mobile_notifications.signals import push_notification_sent
from apps.profiles.models import Profile

DEVICE_CLASSES = (
    # APNSDevice,
    GCMDevice,
)


def _get_assignments(device_class):
    assignments = {
        APNSDevice: {
            # put here assignment: application_id
        },
        GCMDevice: {
            # put here assignment: application_id
        },
    }
    return assignments.get(device_class)


class Pusher(object):
    def __init__(
        self,
        profile,
        message=None,
        subject=None,
        application_assignment=None,
        payload=None,
        **kwargs,
    ):
        self._profile = profile
        self._subject = subject
        self._message = message
        self.application_assignment = application_assignment
        self.raise_error = kwargs.pop("raise_error", True)
        self.payload = payload or {}
        self.payload.setdefault(TARGET_SCREEN, "default")
        self.kwargs = kwargs
        self.event_labels = {}

    @property
    def subject(self):
        return self._subject

    @property
    def message(self):
        return self._message

    @property
    def profile_pk(self):
        return self._profile.pk if isinstance(self._profile, Profile) else self._profile

    def deactivate_device(self, device):
        device.active = False
        device.save(update_fields=["active"])

    def deactivate_all_devices(self):
        for device_class in DEVICE_CLASSES:
            self.get_devices(device_class).update(active=False)

    def reactivate_all_devices(self):
        for device_class in DEVICE_CLASSES:
            self.get_devices(device_class, active=False).update(active=True)

    def _send(self, device, message, **params):
        """
        :rtype: (dict | None)
        :returns: json response from push_notifications request to GCM/APNS gateway
        :raises: APNSServerError, GCMError
        """
        result = None
        try:
            result = device.send_message(message=message, **params)
        except GCMError as error:
            logging.error(
                error.args if error.args else tuple(),
                extra={'device': device, 'forwarded_message': message},
            )
            if self.raise_error:
                raise
            try:
                if (
                    "NotRegistered" in error.message
                    or isinstance(error.message, dict)
                    and error.message["results"][0]["error"] == "NotRegistered"
                ):
                    self.deactivate_device(device)
            except Exception:  # pylint: disable=W0703
                pass
        except APNSServerError as error:
            logging.error(
                error.args if error.args else tuple(),
                extra={"device": device, "forwarded_message": message},
            )
            if self.raise_error:
                raise
            try:
                # 8 - Invalid token
                if error.status == 8:
                    self.deactivate_device(device)
            except Exception:  # pylint: disable=W0703
                pass

        else:
            self._write_log(message, device, **params)
            if isinstance(device, APNSDevice) and not result:
                # crutch for apple devices - by default result is None,
                # but we need to check result outside this method.
                # So - build pseudo-result.
                result = {
                    "status": "success",
                    "device_type": device.__class__.__name__,
                    "device_id": device.id,
                }

        return result

    def _get_application_id(self, device_class):
        try:
            application_id = _get_assignments(device_class).get(self.application_assignment)
        except (AttributeError, KeyError):
            application_id = None

        return application_id

    def get_devices(self, klass, active=True):
        queryset = klass.objects.filter(user__profile__pk=self.profile_pk, active=active)
        if self.application_assignment:
            application_id = self._get_application_id(klass)
            if application_id:
                queryset = queryset.filter(application_id=application_id)
        return queryset

    def send_to_all_devices(self):
        """
        :return: list of sent pushes.
        Every sent push is
        >>> {"push_uuid": push_uuid, "event_labels": self.event_labels}
        :rtype: list of dict
        """
        if not self.subject:
            raise ValueError("No subject supplied")
        if not self.message:
            raise ValueError("No message supplied")

        assert self.payload.get(TARGET_SCREEN)
        sent_pushes = []
        for device_class in DEVICE_CLASSES:
            params = {}
            if device_class == APNSDevice:  # apple
                send_message = {  # next move to `alert`
                    BODY: self.message,
                }
                if self.subject:
                    send_message[TITLE] = self.subject
                params["sound"] = "default"
                params["badge"] = 1
                params["mutable_content"] = 1
                if self.payload:
                    params[EXTRA] = {PAYLOAD: self.payload}
            else:  # android
                title = self.subject
                body = self.message
                send_message = body

                # FCM_NOTIFICATIONS_PAYLOAD_KEYS
                # "title", "body", "icon", "sound", "badge", "color", "tag", "click_action",
                # "body_loc_key", "body_loc_args", "title_loc_key", "title_loc_args"
                params[EXTRA] = {
                    TITLE: title,
                    BODY: body,
                    "extra_title": title,
                    "extra_body": body,
                    "message": body,
                }
                if self.payload:
                    params[EXTRA].update(self.payload)

            devices = self.get_devices(device_class, active=True)
            for device in devices.iterator():
                push_uuid = generate_uuid()

                params.setdefault(EXTRA, {})
                params[EXTRA]["uuid"] = push_uuid
                if self.event_labels:
                    params[EXTRA]["event_labels"] = self.event_labels

                result = self._send(device, message=send_message, **params)
                if result:
                    push_notification_sent.send(
                        push_uuid=push_uuid, event_labels=self.event_labels, sender=self.__class__
                    )
                    sent_pushes.append(
                        {"push_uuid": push_uuid, "event_labels": self.event_labels,}
                    )
        return sent_pushes

    def _write_log(self, message, device, **params):
        data = {
            "recipient_profile_pk": self.profile_pk,
            "device": device,
            "device_id": device.id,
            "device_type": device.__class__.__name__,
            "registration_id": device.registration_id,
            "subject": self.subject,
            "original_message": self.message,
            "application_assignment": self.application_assignment,
        }
        if device.device_id:
            data["device_uuid"] = device.device_id
        data.update(**self.kwargs)
        data.update(**params)
        RecordLog("graylog.push_log").warn(data.get("text") or self.message, extra=data)


# @mute_errors
def send_to_profile(*args, **kwargs):
    """
    :return: list of sent pushes.
    Every sent push is
    >>> {"push_uuid": "some UUID", "event_labels": {}}
    :rtype: list of dict
    """
    pusher = Pusher(*args, **kwargs)
    sent_pushes = pusher.send_to_all_devices()
    return sent_pushes
