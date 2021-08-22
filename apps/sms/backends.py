import logging
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.core.mail import send_mail
from django.test import override_settings

from apps.core.meta import Singleton
from apps.sms.constants import FAKE_OPERATOR_CODE


class BaseBackend:
    settings = None

    def __init__(self, **kwargs):
        self.settings = {}
        self.settings.update(kwargs)
        logger_name = f'{self.__module__}.{self.__class__.__name__}'
        # print(f"{self=}, {logger_name=}")
        self.log = logging.getLogger(logger_name)

    def send(self, to, body):
        raise NotImplementedError()


class HttpBackend(BaseBackend):
    def send(self, to, body):
        if to[1:4] != FAKE_OPERATOR_CODE:
            self.log.info(f'Sending a message to {to}: {body}')
            return self._call_gateway(self._get_gateway_url(), self._get_gateway_params(to, body))

    def _call_gateway(self, url: str, params: dict) -> requests.Response:
        self.log.debug(f'Calling gateway: {url}/{urlencode(params)}')
        response: requests.Response = requests.post(url, data=params)
        logging.debug(f"{self.__class__.__name__} {response.status_code=}, {response.content=}")
        if "error" in response.text:
            phone: str = params['phones']
            if phone.startswith("7139"):
                pass
            else:
                logging.error(
                    "Cannot send SMS",
                    extra={
                        "response": response,
                        "response_code": response.status_code,
                        "response_text": response.text,
                        "class": f"{self.__class__.__name__}",
                    },
                )
        return response

    def _get_gateway_params(self, to, body):
        return {
            'login': self.settings['GATEWAY_LOGIN'],
            'psw': self.settings['GATEWAY_PASSWORD'],
            'charset': 'utf-8',
            'fmt': 3,
            'cost': 2,
            'phones': to,
            'mes': body.encode('utf-8'),
            'sender': self.settings['SENDER'],
        }

    def _get_gateway_url(self):
        return self.settings['GATEWAY_URL']


class ConsoleBackend(BaseBackend):
    def send(self, to, body):
        self.log.info('Pretending to send a message to %s: %s', to, body)


class MuteBackend(BaseBackend):
    def send(self, to, body):
        pass


class TestingBackend(BaseBackend):
    __metaclass__ = Singleton

    outbox = []

    def send(self, to, body):
        self.outbox.append((to, body))

    def reset(self):
        self.outbox = []

    def assert_sent(self, *args):
        for message in args:
            if message not in self.outbox:
                raise AssertionError('Message "{}" was not sent to {}'.format(*message))


class SmsAsEmailBackend(BaseBackend):
    def __init__(self, **kwargs):
        super(SmsAsEmailBackend, self).__init__(**kwargs)
        assert settings.EMAIL_HOST_FOR_SMS, settings.EMAIL_HOST_FOR_SMS
        assert settings.EMAIL_PORT_FOR_SMS, settings.EMAIL_HOST_FOR_SMS

        self.recipient = settings.SMS_AS_EMAIL_RECIPIENT
        self.email_host = settings.EMAIL_HOST_FOR_SMS
        self.email_port = settings.EMAIL_PORT_FOR_SMS
        self.from_email = settings.DEFAULT_FROM_EMAIL

    def send(self, to, body):
        subject = 'SMS на {}'.format(to)
        with override_settings(
            EMAIL_HOST=self.email_host, EMAIL_PORT=self.email_port, EMAIL_USE_TLS=False
        ):
            send_mail(subject, body, self.from_email, [self.recipient])


class BeelineHttpBackend(HttpBackend):
    def _call_gateway(self, url, params):
        self.log.debug(f'Calling gateway: {url}; params={params}')
        response = requests.post(url, headers=self._get_gateway_headers(), data=params,)
        logging.debug(f"BeelineHttpBackend {response.status_code=}, {response.content=}")
        if "error" in response.text:
            logging.error(
                "Cannot send Beeline SMS",
                extra={
                    "response": response,
                    "response_code": response.status_code,
                    "response_text": response.text,
                },
            )
            # response.status_code = 400
        return response

    def _get_gateway_headers(self):
        return {'Content-Type': 'application/x-www-form-encoded'}

    def _get_gateway_params(self, to, body):
        return {
            'user': self.settings['GATEWAY_LOGIN'],
            'pass': self.settings['GATEWAY_PASSWORD'],
            'action': 'post_sms',
            'target': ",".join([to]),
            'message': body.encode('utf-8'),
            'sender': self.settings['SENDER'] or None,
        }
