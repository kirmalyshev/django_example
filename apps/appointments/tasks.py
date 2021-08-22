from datetime import timedelta

import logging
from celery.schedules import crontab
from django.utils import timezone

from apps.appointments.constants import AppointmentStatus
from apps.appointments.selectors import AllAppointmentsSelector, TimeSlots
from apps.appointments.workflows import (
    TimeSlotWorkflow,
    AppointmentWorkflow,
    AppointmentNotificationWorkflow,
)
from apps.core.utils import crontab_in_default_tz
from apps.feature_toggles.constants import (
    APPOINTMENT__MARK_FINISHED_WHEN_WORKDAY_FINISHED,
    APPOINTMENT__MARK_FINISHED_IN_N_MIN,
)
from apps.feature_toggles.models import Feature
from apps.feature_toggles.utils import is_feature_enabled
from apps.tools.tasks import LastLaunchTimeBaseTask, OneAtATimeTask


class DisableOldTimeSlots(OneAtATimeTask):
    run_every = crontab(minute='*/12')

    def start(self):
        available_timeslots = TimeSlots().free_past()
        TimeSlotWorkflow.bulk_mark_busy(available_timeslots)


class RemindAboutPlannedAppointmentsTask(LastLaunchTimeBaseTask):
    """
    Send PUSH notifications about planned appointments
    """

    launch_minutes_delta = 1
    run_every = crontab(minute="*/1")
    last_launch_key = 'REMIND_ABOUT_PLANNED_APPOINTMENTS__LAST_LAUNCH_TIME'

    def get_appointments(self, minutes_before_appointment):
        """
        :returns: appointments with
        (last_launch_time + gap) < appointment.start <= (current_launch_time + gap)
        :rtype: apps.appointments.managers.AppointmentQuerySet
        """
        if not self.current_launch_time:
            raise ValueError(f'{self.__class__} instance must have current_launch_time attribute.')
        bottom_bound = self.last_launch_time + timedelta(minutes=minutes_before_appointment)
        upper_bound = self.current_launch_time + timedelta(
            minutes=minutes_before_appointment - 1, seconds=59
        )  # чтобы исключить попадание записи дважды в таск

        appointments = (
            AllAppointmentsSelector()
            .future_planned()
            .with_active_users()
            .filter(start__range=(bottom_bound, upper_bound))
            .select_related("patient__profile")
            .prefetch_related("patient__profile__users")
        )
        return appointments

    def remind_before_specific_minutes(self, minutes_value):
        appointments = self.get_appointments(minutes_before_appointment=minutes_value)
        if not appointments.exists():
            print(f'--- no appointments found for {minutes_value / 60} hours')
            return
        for appointment in appointments.iterator():
            AppointmentNotificationWorkflow.remind_about_planned_appointment(
                appointment, by_celery_task=False
            )

    def start(self):
        minutes_before_appointment = (2 * 60, 24 * 60)
        for minutes_value in minutes_before_appointment:
            self.remind_before_specific_minutes(minutes_value)


class FinishYesterdayAppointmentsTask(OneAtATimeTask):
    run_every = crontab_in_default_tz(minute=0, hour=4)  # in settings.TIME_ZONE

    @staticmethod
    def _get_yesterday_appointments():
        today = timezone.localdate()
        yesterday = today - timedelta(days=1)
        return (
            AllAppointmentsSelector()
            .visible_by_patient__active()
            .start_on_date(yesterday)
            .filter(
                status__in=(
                    AppointmentStatus.PLANNED,
                    AppointmentStatus.PATIENT_ARRIVED,
                    AppointmentStatus.AWAITING_PAYMENT,
                    AppointmentStatus.ON_APPOINTMENT,
                )
            )
        )

    def start(self):
        if not is_feature_enabled(APPOINTMENT__MARK_FINISHED_WHEN_WORKDAY_FINISHED):
            return

        appointments = self._get_yesterday_appointments()
        for appointment in appointments.iterator():
            AppointmentWorkflow.finish(appointment)


class FinishEndedAppointmentsTask(OneAtATimeTask):
    launch_delta_minutes = 6
    run_every = crontab_in_default_tz(minute='*/6')  # in settings.TIME_ZONE

    @classmethod
    def _get_previous_appointments(cls, delta_minutes: int = 30):
        now = timezone.now()
        delta = timedelta(minutes=delta_minutes)
        to_time = now - delta
        from_time = to_time - timedelta(minutes=cls.launch_delta_minutes + 1)
        return (
            AllAppointmentsSelector()
            .visible_by_patient__active()
            .filter(
                status__in=(
                    AppointmentStatus.PLANNED,
                    AppointmentStatus.PATIENT_ARRIVED,
                    AppointmentStatus.AWAITING_PAYMENT,
                    AppointmentStatus.ON_APPOINTMENT,
                ),
                end__lte=to_time,
            )
        )

    def start(self):
        task_name = self.__class__.__name__
        # logging.debug(f"start {task_name}")
        if not is_feature_enabled(APPOINTMENT__MARK_FINISHED_IN_N_MIN):
            logging.warning(
                f"feature {APPOINTMENT__MARK_FINISHED_IN_N_MIN} is disabled. Task is stopped"
            )
            return

        feature = Feature.objects.get(system_code=APPOINTMENT__MARK_FINISHED_IN_N_MIN)
        delta_value = feature.value or "30"
        delta_value = int(delta_value)

        appointments = self._get_previous_appointments(delta_minutes=delta_value)
        count = appointments.count()
        for appointment in appointments.iterator():
            AppointmentWorkflow.finish(appointment, ask_for_review=True)
        logging.debug(f"{task_name}: finished {count} appointments")
