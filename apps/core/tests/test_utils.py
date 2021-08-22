from datetime import datetime
from unittest import TestCase

from django.utils import timezone
from freezegun import freeze_time

from apps.core.utils import is_now_workday, now_in_default_tz


def datetime_to_freezable_str(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S%z")


class IsNowWorkdayTest(TestCase):
    def setUp(self) -> None:
        self.tzinfo = timezone.get_default_timezone()

    def test__is_now_workday__night(self):
        current_freezed = datetime(
            year=2021, month=5, day=19, hour=0, minute=59, tzinfo=self.tzinfo
        )
        freezed_str = datetime_to_freezable_str(current_freezed)
        with freeze_time(freezed_str):
            self.assertFalse(is_now_workday())

    def test__is_now_workday__before_7(self):
        current_freezed = datetime(
            year=2021, month=5, day=19, hour=6, minute=59, tzinfo=self.tzinfo
        )
        freezed_str = datetime_to_freezable_str(current_freezed)
        with freeze_time(freezed_str):
            now = now_in_default_tz()
            self.assertFalse(is_now_workday(), now)

    def test__is_now_workday__morning_true(self):
        current_freezed = datetime(2021, 5, 19, hour=7, minute=50, second=12, tzinfo=self.tzinfo)
        freezed_str = datetime_to_freezable_str(current_freezed)

        with freeze_time(freezed_str):
            value = is_now_workday()
            now = now_in_default_tz()
            self.assertTrue(value, now)

    def test__is_now_workday__morning_true_2(self):
        current_freezed = datetime(2021, 5, 19, hour=7, minute=51, tzinfo=self.tzinfo)
        freezed_str = datetime_to_freezable_str(current_freezed)

        with freeze_time(freezed_str):
            value = is_now_workday()
            now = now_in_default_tz()
            self.assertTrue(value, now)

    def test__is_now_workday__day_true(self):
        current_freezed = datetime(
            year=2021, month=5, day=19, hour=13, minute=19, tzinfo=self.tzinfo
        )
        freezed_str = datetime_to_freezable_str(current_freezed)
        with freeze_time(freezed_str):
            value = is_now_workday()
            self.assertTrue(value, now_in_default_tz())

    def test__is_now_workday__evening_true(self):
        current_freezed = datetime(
            year=2021, month=5, day=19, hour=19, minute=21, tzinfo=self.tzinfo
        )
        freezed_str = datetime_to_freezable_str(current_freezed)
        # print(f"{freezed_str=}")
        with freeze_time(freezed_str):
            value = is_now_workday(print=True)
            self.assertTrue(value, now_in_default_tz())

    def test__is_now_workday__evening_false(self):
        current_freezed = datetime(
            year=2021, month=5, day=19, hour=20, minute=00, tzinfo=self.tzinfo
        )
        freezed_str = datetime_to_freezable_str(current_freezed)
        with freeze_time(freezed_str):
            value = is_now_workday()
            self.assertFalse(value, now_in_default_tz())

        current_freezed = datetime(
            year=2021, month=5, day=19, hour=20, minute=1, tzinfo=self.tzinfo
        )
        freezed_str = datetime_to_freezable_str(current_freezed)
        with freeze_time(freezed_str):
            value = is_now_workday()
            self.assertFalse(value, now_in_default_tz())

        current_freezed = datetime(
            year=2021, month=5, day=19, hour=22, minute=15, tzinfo=self.tzinfo
        )
        freezed_str = datetime_to_freezable_str(current_freezed)
        with freeze_time(freezed_str):
            value = is_now_workday()
            self.assertFalse(value, now_in_default_tz())
