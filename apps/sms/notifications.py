from apps.core.backends import BaseNotifyBackend
from .handlers import send


class SmsBackend(BaseNotifyBackend):
    @property
    def contact_type(self):
        from apps.profiles.models import Contact

        return Contact.PHONE

    def send(self, user, message, *args, **kwargs):
        assert user, user
        contact_to = kwargs.get('phone_value') or user.get_notification_phone()
        if contact_to:
            send(contact_to, message)
            self.log_message(text_message=message, contact_to=contact_to, user=user, **kwargs)
