# encoding=utf-8
from functools import wraps

from django.test import override_settings

from .backends import TestingBackend


class assert_sends_sms:
    def __init__(self, sms_counter=1, phones=None, body=None, test=None):
        assert not sms_counter or phones and body
        self.sms_counter = sms_counter
        self.test = test
        self.body = body if isinstance(body, list) else [body]
        self.phones = phones if isinstance(phones, list) else [phones]
        self.testing_backend_setting = override_settings(
            SMS_BACKEND='apps.sms.backends.TestingBackend', SMS_DISABLED=False
        )

    def __call__(self, func):
        @wraps(func)
        def inner(*args, **kwargs):
            self.test = self.test or args[0]
            with self:
                result = func(*args, **kwargs)
            return result

        return inner

    def __exit__(self, exception_type, exception_value, traceback):
        if exception_type and issubclass(exception_type, Exception):
            raise (exception_type, exception_value, traceback)

        outbox = TestingBackend.outbox
        if outbox:
            flat_outbox = ', outbox contents:\n' + '\n'.join(
                ['{}: {}'.format(n, m) for n, m in outbox]
            )
        else:
            flat_outbox = ''
        message = 'Expected {} SMS, sent {}{}'.format(self.sms_counter, len(outbox), flat_outbox)
        self.test.assertEqual(len(outbox), self.sms_counter, message)

        for expected_phone, expected_body, counter in zip(
            self.phones, self.body, range(self.sms_counter)
        ):
            actual_phone, actual_body = outbox[counter]
            if hasattr(expected_body, 'match'):
                self.test.assertRegexpMatches(actual_body, expected_body)
            else:
                self.test.assertEqual(actual_body, expected_body)
            self.test.assertEqual(actual_phone, expected_phone)

        self.testing_backend_setting.disable()

    def __enter__(self):
        assert self.test
        self.testing_backend_setting.enable()
        TestingBackend.outbox = []
        self.test.assertEqual(len(TestingBackend.outbox), 0)
        return self
