# encoding=utf-8

from __future__ import unicode_literals

from django.core.management.base import BaseCommand

from apps.appointments.tasks import disable_old_timeslots


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        disable_old_timeslots()
