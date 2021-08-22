# coding: utf-8
import copy

from apps.core.decorators import run_if_setting_true, run_if_setting_false
from apps.logging.utils import RecordLog


class BaseNotifyBackend:
    def __init__(self, log=True):
        self.log = log

    def send(self, user, message, subject, *args, **kwargs):
        raise NotImplementedError()

    # @run_if_setting_false('LOAD_FIXTURE_MODE')
    @run_if_setting_true('USE_NOTIFY_LOG')
    def log_message(self, **kwargs):
        if not self.log:
            return

        user = kwargs.get('user')
        data = copy.copy(kwargs)

        email = user.contacts.get_emails().filter(is_primary=True).first() if user else None
        if email:
            data['to_user_email'] = email.value

        contact_type = self.__class__.__name__

        data.update({'to_user_id': user.id if user else '', 'contact_type': contact_type})

        if 'name' in data:
            data['event_name'] = data.pop('name')

        log_title = (
            f"{data.get('event_name')} {data.get('contact_to')}. "
            f"type: {contact_type}. subject: {data.get('subject', '')}"
        )
        RecordLog('graylog.notifications').warn(log_title, extra=data)
