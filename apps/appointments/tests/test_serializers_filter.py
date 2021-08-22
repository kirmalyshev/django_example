from unittest import TestCase

from rest_framework.exceptions import ValidationError, ErrorDetail

from apps.appointments.constants import ONLY_FUTURE, ONLY_PAST
from apps.appointments.serializers_filter import AppointmentsFilterParamsSerializer


class AppointmentsFilterParamsSerializerTest(TestCase):
    maxDiff = None
    serializer_class = AppointmentsFilterParamsSerializer

    def test_both_only_future_and_only_past(self):
        init_data = {ONLY_FUTURE: True, ONLY_PAST: True}
        serializer = self.serializer_class(data=init_data)
        with self.assertRaises(ValidationError) as err_context:
            serializer.is_valid(raise_exception=True)
        self.assertEqual(
            {
                'non_field_errors': [
                    ErrorDetail(
                        string='only one of "only_future" OR "only_past" can be in params',
                        code='invalid',
                    )
                ]
            },
            err_context.exception.detail,
        )
