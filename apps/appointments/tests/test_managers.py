from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from freezegun import freeze_time

from apps.appointments.factories import TimeSlotFactory
from apps.appointments.models import TimeSlot


@freeze_time('2020-01-20')
class TimeSlotQuerySetTest(TestCase):
    def test_intersects_with_start(self):
        now = timezone.now()
        start_1 = now + timedelta(minutes=10)
        end_1 = now + timedelta(minutes=20)
        start_2 = now + timedelta(days=1, minutes=10)
        end_2 = now + timedelta(days=1, minutes=20)
        ts_1 = TimeSlotFactory(start=start_1, end=end_1)
        ts_2 = TimeSlotFactory(start=start_2, end=end_2)

        qs_1 = TimeSlot.objects.intersects_with_start(start=start_1 + timedelta(minutes=5))
        self.assertEqual([ts_1.id], list(qs_1.values_list('id', flat=True)))

        qs_2 = TimeSlot.objects.intersects_with_start(start=start_2 + timedelta(minutes=5))
        self.assertEqual([ts_2.id], list(qs_2.values_list('id', flat=True)))
