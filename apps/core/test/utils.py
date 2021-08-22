# encoding=utf-8

import base64

from mock import ANY, Mock, patch
from rest_framework.test import APIClient

from ..utils import generate_random_id


def random_email():
    return '{}@{}.ru'.format(generate_random_id(10), generate_random_id(10))


def assert_dates_equal(
    date1, date2, message='Datetimes are {} second(s) apart, should be within {}', delta=2
):
    """
    Assert two datetimes difference is within a given delta (2 seconds by default)
    """
    actual_delta = (max(date1, date2) - min(date1, date2)).seconds
    assert delta >= actual_delta, message.format(actual_delta, delta)


# def patch_actual_region_timezone(mock_timezone=None, notify_hour=0, wrong_timezone=False):
#     now = datetime.utcnow()
#     for tzone in pytz.common_timezones:
#         if wrong_timezone:
#             if pytz.timezone(tzone).fromutc(now).hour not in settings.ORDERFILTER_NOTIFY_HOURS:
#                 timezone = tzone
#                 break
#         else:
#             if pytz.timezone(tzone).fromutc(now).hour == settings.ORDERFILTER_NOTIFY_HOURS[notify_hour]:
#                 timezone = tzone
#                 break
#
#     if mock_timezone is None:
#         if timezone not in Region.TIMEZONES:
#             dump_timezones = copy.copy(Region.TIMEZONES)
#             mock_timezone = patch(
#                 'apps.directory.models.Region.TIMEZONES',
#                 new_callable=PropertyMock,
#                 return_value=dump_timezones + [timezone]
#             )
#             mock_timezone.start()
#     else:
#         if timezone not in mock_timezone.kwargs['return_value']:
#             mock_timezone.kwargs['return_value'] += [timezone]
#
#     return timezone, mock_timezone


class assert_signal_sent(object):
    """Assert signal is sent with given arguments

    Example:
    >>> with assert_signal_sent(signal, sender=ModelClass, instance=obj):
    ...    make_some_stuff()
    ...

    More complex example:
    >>> with assert_signal_sent(target_signal) as sent_signal:
    ...    make_some_stuff()
    ...    self.assertEqual(sent_signal.call_args['sender'], SomeClass)
    ...    self.assertTrue(
    ...        re.match(r'^[0-9a-z-]{36}$', sent_signal.call_args['uuid'],
    ...        'invalid uuid passed to signal'
    ...    )
    ...
    """

    def __init__(self, signal, **kwargs):
        self.signal = signal
        self.kwargs = kwargs

    def __enter__(self):
        self.handler = Mock()
        self.signal.connect(self.handler)

        return self

    def check_signal(self):
        if self.kwargs:
            self.kwargs.setdefault('sender', ANY)
            self.handler.assert_called_with(signal=self.signal, **self.kwargs)
        else:
            assert self.handler.call_args[1]['signal'] == self.signal

    @property
    def call_args(self):
        # Signals are called using named arguments, so we can omit positional ones
        return self.handler.call_args[1]

    def __exit__(self, exception_type, exception_value, traceback):
        if exception_type and issubclass(exception_type, Exception):
            raise exception_type(exception_value).with_traceback(traceback)

        self.check_signal()
        self.signal.disconnect(self.handler)


class assert_signal_not_sent(assert_signal_sent):
    """Assert that specified signal wasn't send

    Example:
    >>> with assert_signal_not_sent(signal, sender=ModelClass, instance=obj):
    ...    make_some_stuff()
    ...
    """

    def check_signal(self):
        self.handler.assert_not_called()


class freeze_target(object):
    """Freeze (cache) target function results for subsequent calls.

    Example:
        >>> def test_func():
        ...     import random
        ...     return [random.randint(1, 50) for _ in range(5)]
        ...
        >>>
        >>> print(test_func())
        [29, 40, 28, 29, 49]
        >>>
        >>> with freeze_target('random.randint'):
        ...     print(test_func())
        ...
        [27, 27, 27, 27, 27]
    """

    def __init__(self, target):
        self._target = target

    def __enter__(self):
        (self._original, _) = patch(self._target).get_original()

        def wrapper(*args, **kwargs):
            if not hasattr(wrapper, '_cached_value'):
                wrapper._cached_value = self._original(*args, **kwargs)
            return wrapper._cached_value

        self._mock_patch = patch(self._target, new=wrapper)
        self._mock_patch.start()

        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self._mock_patch.stop()

        if exception_type and issubclass(exception_type, Exception):
            raise exception_type(exception_value).with_traceback(traceback)


class BasicAuthClient(APIClient):
    username = None
    password = None

    def __init__(self, *args, **kwargs):
        super(BasicAuthClient, self).__init__(*args, **kwargs)
        credentials = base64.b64encode(self.username + ':' + self.password)
        self.defaults['HTTP_AUTHORIZATION'] = 'Basic ' + credentials


def get_api_error_title(response, parameter, code) -> str:
    """
    Return expected error title (error description) from response
    by parameter (field in Serializer or Model) and error code (e.g. 'validation_error').

    :type response: rest_framework.response.Response
    :type parameter: str
    :type code: str
    """
    api_errors = response.data['api_errors']
    errors = [e for e in api_errors if e['source']['parameter'] == parameter and e['code'] == code]
    assert errors, 'There are no such errors'
    error = errors[0]
    title = error['title']
    return title
