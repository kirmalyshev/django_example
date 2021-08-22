import logging
from datetime import timedelta
from typing import Dict, Optional, Set, TypedDict

from django.db import transaction

from apps.appointments.constants import (
    CreateAppointmentDict,
    UpdateAppointmentDict,
    AppointmentStatus,
    CreateTimeSlotIntegrationDict,
    UpdateTimeSlotIntegrationDict,
    APPOINTMENT_REQUEST__REJECTED_BY_ADMIN,
    REMIND_ABOUT_PLANNED_APPOINTMENT,
    APPOINTMENT_CANCELED_BY_ADMIN,
    APPOINTMENT_REQUEST__APPROVED_BY_ADMIN,
    AppointmentCreatedValues,
    DOCTOR_ID,
    PATIENT_ID,
    SUBSIDIARY_ID,
    SERVICE_ID,
    TARGET_PATIENT_ID,
    REASON_TEXT,
    CreateAppointmentByPatientDict,
)
from apps.appointments.exceptions import TooManyNearbyAppointments, NoStartEndValuesError
from apps.appointments.managers import TimeSlotQuerySet
from apps.appointments.models import (
    Appointment,
    TimeSlot,
    TimeSlotToAppointment,
)
from apps.appointments.selectors import AllAppointmentsSelector, DoctorTimeSlots, TimeSlots
from apps.appointments.utils import AppointmentUtils
from apps.appointments.validators import (
    AppointmentValidator,
    AppointmentModerationValidator,
)
from apps.clinics.models import Patient
from apps.notify import send_event
from apps.notify.constants import PUSH
from apps.reviews.workflow import ReviewWorkflow


class BaseAppointmentWorkflow:
    @classmethod
    def _make_timeslots_free(cls, appointment: Appointment):
        timeslots = appointment.time_slots.all()
        if not timeslots.exists():
            return
        TimeSlotWorkflow.bulk_mark_free(timeslots, remove_appointment_links=True)


class AppointmentModerationWorkflow(BaseAppointmentWorkflow):
    validator = AppointmentModerationValidator
    model = Appointment

    @classmethod
    def reject_by_moderator(cls, appointment: Appointment, **kwargs) -> Appointment:
        """ отклонить Запись на прием """
        if kwargs.get('should_validate', True):
            cls.validator.validate_before_reject(appointment, **kwargs)
        appointment.mark_rejected()
        cls._make_timeslots_free(appointment)
        AppointmentNotificationWorkflow.notify__rejected_by_admin(appointment)
        return appointment

    @classmethod
    def approve(cls, appointment: Appointment, **kwargs) -> Appointment:
        """ одобрить Запись на прием """
        if kwargs.get('should_validate', True):
            cls.validator.validate_before_approve(appointment)
        appointment.mark_planned(save=True)
        if kwargs.get('should_notify', True):
            AppointmentNotificationWorkflow.notify__approved_by_moderator(appointment)
        return appointment

    @classmethod
    def return_to_moderation(cls, appointment: Appointment) -> Appointment:
        """ вернуть Запись на прием обратно на модерацию """
        cls.validator.validate_before_return_to_moderation(appointment)
        appointment.mark_on_moderation()
        return appointment


class AppointmentWorkflow(BaseAppointmentWorkflow):
    """
    Все бизнес процессы, связанные с Записями на прием.
    * Создать
    * Отклонить
    * Одобрить
    * Сменить статус на нужный
    * Завершить
    """

    model = Appointment
    validator = AppointmentValidator

    @classmethod
    @transaction.atomic
    def _create_instance(cls, author_patient: Patient, **data) -> Appointment:
        start = data.get('start')  # TODO remove start/end, deprecated
        end = data.get('end')
        time_slot_id = data.get('time_slot_id')
        time_slot = None
        if time_slot_id:
            time_slot = TimeSlot.objects.get(id=time_slot_id)
            start = time_slot.start
            end = time_slot.end

        subsidiary_id = data.get(SUBSIDIARY_ID)
        service_id = data.get(SERVICE_ID)
        doctor_id = data.get(DOCTOR_ID)
        reason_text = data.get(REASON_TEXT)
        target_patient_id = data.get(TARGET_PATIENT_ID)
        if not target_patient_id:
            target_patient_id = author_patient.id

        appointment = cls.model.objects.create(
            patient_id=target_patient_id,
            author_patient=author_patient,
            start=start,
            end=end,
            doctor_id=doctor_id,
            subsidiary_id=subsidiary_id,
            service_id=service_id,
            reason_text=reason_text,
            status=cls.model.status_enum.ON_MODERATION,
            created_by_type=AppointmentCreatedValues.PATIENT,
        )
        if time_slot:
            TimeSlotWorkflow.link_with_appointment(time_slot, appointment)

        return appointment

    @classmethod
    def get_integration_workflow(cls):
        from apps.integration.get_workflow import get_integration_workflow

        return get_integration_workflow()

    @classmethod
    def create_by_patient(
        cls, author_patient: Patient, incoming_data: CreateAppointmentByPatientDict
    ) -> Appointment:
        """ Создать Заявку на прием """
        print(f"AppointmentWorkflow.create_by_patient")
        print(f"{incoming_data=}")
        data = cls.validator.validate_create_data(data=incoming_data, author_patient=author_patient)
        print(f"{data=}")
        appointment = cls._create_instance(author_patient, **data)
        print(f"created {appointment=}")

        integration_workflow = cls.get_integration_workflow()
        if integration_workflow:
            integration_workflow.create_appointment_by_patient(
                appointment_id=appointment.id,
                author_patient_id=author_patient.id,
                run_as_task=True,
            )
        return appointment

    @classmethod
    def cancel_by_patient(cls, appointment: Appointment, patient: Patient, **kwargs) -> Appointment:
        """ Отменить Запись - пациент сам отменяет свою запись """
        cls.validator.check_before_cancel_by_patient(appointment, patient)
        appointment.mark_canceled_by_patient()

        integration_workflow = cls.get_integration_workflow()
        if integration_workflow:
            integration_workflow.cancel_appointment_by_patient(
                appointment_id=appointment.id, author_patient=patient, run_as_task=True
            )
        return appointment

    @classmethod
    def finish(cls, appointment: Appointment, ask_for_review: bool = False) -> None:
        appointment.mark_finished(save=True)
        if ask_for_review:
            ReviewWorkflow.ask_for_appointment_review(appointment)

    @classmethod
    def cancel_by_moderator(cls, appointment: Appointment, **kwargs) -> Appointment:
        appointment.mark_canceled_by_moderator(save=True)
        cls._make_timeslots_free(appointment)
        AppointmentNotificationWorkflow.notify__cancel_by_moderator(appointment)
        return appointment

    @classmethod
    def create_from_integration_data(cls, data: CreateAppointmentDict) -> Appointment:
        data['created_by_type'] = AppointmentCreatedValues.ADMINISTRATOR
        new_appointment: Appointment = Appointment.objects.create(**data)
        return new_appointment

    @classmethod
    def update_from_integration_data(
        cls, appointment: Appointment, update_data: UpdateAppointmentDict, should_save: bool = True
    ) -> Appointment:
        start = update_data['start']
        end = update_data['end']
        subsidiary_id = update_data['subsidiary_id']
        patient_id = update_data['patient_id']
        doctor_id = update_data['doctor_id']
        service_id = update_data['service_id']
        status = update_data['status']
        integration_data = update_data['integration_data']

        if appointment.is_canceled_by_patient and status in AppointmentStatus.CANCELED_VALUES:
            pass
        else:
            appointment.status = status
        appointment.start = start
        appointment.end = end
        appointment.subsidiary_id = subsidiary_id
        appointment.patient_id = patient_id
        appointment.doctor_id = doctor_id
        appointment.service_id = service_id
        if integration_data and appointment.integration_data != integration_data:
            appointment.integration_data = integration_data

        if should_save:
            appointment.save()
        return appointment

    @classmethod
    def update_start_end_from_linked_timeslots(cls, appointment: Appointment) -> Appointment:
        timeslots = appointment.time_slots.all().order_by('start')
        first_timeslot: TimeSlot = timeslots.earliest('start')
        last_timeslot: TimeSlot = timeslots.latest('start')
        should_save: bool = False

        if appointment.start != first_timeslot.start:
            appointment.start = first_timeslot.start
            should_save = True
        if appointment.end != last_timeslot.end:
            appointment.end = last_timeslot.end
            should_save = True

        if should_save:
            appointment.save()
        return appointment

    @classmethod
    def make_planned(cls, obj: Appointment, should_remind=True, **kwargs) -> Appointment:
        obj.mark_planned(save=True)
        if should_remind:
            AppointmentNotificationWorkflow.remind_about_planned_appointment(
                appointment=obj, by_celery_task=True, event_name=kwargs.get('event_name')
            )
        return obj

    @classmethod
    def merge_nearby_appointments_and_new_timeslot(
        cls, appointment_ids, timeslot_id
    ) -> Optional[Appointment]:
        appointments = (
            AllAppointmentsSelector().all_with_prefetched().filter(id__in=appointment_ids)
        )
        # region check that appointments - are for same doctor, patient, subsidiary
        doctor_ids_count = (
            appointments.values_list(DOCTOR_ID, flat=True)
            .order_by(DOCTOR_ID)
            .distinct(DOCTOR_ID)
            .count()
        )
        if doctor_ids_count > 1:
            return
        patient_ids_count = (
            appointments.values_list(PATIENT_ID, flat=True)
            .order_by(PATIENT_ID)
            .distinct(PATIENT_ID)
            .count()
        )
        if patient_ids_count > 1:
            return
        subsidiary_ids_count = (
            appointments.values_list(SUBSIDIARY_ID, flat=True)
            .order_by(SUBSIDIARY_ID)
            .distinct(SUBSIDIARY_ID)
            .count()
        )
        if subsidiary_ids_count > 1:
            return
        # endregion

        # check that timeslot is close to every found appointment.
        # usually it happens when timeslot is between them
        timeslot: TimeSlot = TimeSlots().get_by_id(timeslot_id)
        allowed_timedelta = timedelta(minutes=1, seconds=1)
        all_appointments_ok_delta = set()
        for appointment in appointments.iterator():
            is_ts_left = timeslot.start < appointment.start
            is_ts_right = timeslot.start > appointment.start
            left_delta = appointment.start - timeslot.end
            right_delta = timeslot.start - appointment.end

            # from left
            if is_ts_left and left_delta <= allowed_timedelta:
                all_appointments_ok_delta.add(appointment.id)
            # from right
            elif is_ts_right and right_delta <= allowed_timedelta:
                all_appointments_ok_delta.add(appointment.id)

        is_timeslot_close_to_appointments: bool = False
        if len(all_appointments_ok_delta) == appointments.count():
            is_timeslot_close_to_appointments = True

        if not is_timeslot_close_to_appointments:
            return

        needed_appointment = appointments.earliest("created")

        for appointment in appointments.exclude(id=needed_appointment.id).iterator():
            appointment: Appointment
            TimeSlotToAppointment.objects.filter(appointment=appointment).update(
                appointment=needed_appointment
            )
            appointment.mark_hidden(save=True)

        return needed_appointment


appointment_workflow = AppointmentWorkflow


class TimeSlotWorkflow:
    @classmethod
    def link_with_appointment(cls, time_slot: TimeSlot, appointment: Appointment) -> None:
        time_slot.mark_unavailable(save=True)
        appointment.time_slots.add(time_slot)

    @classmethod
    def unlink_from_appointment(cls, time_slot: TimeSlot, appointment: Appointment) -> None:
        TimeSlotToAppointment.objects.filter(
            time_slot_id=time_slot.id, appointment_id=appointment.id
        ).delete()
        time_slot.mark_available()

    @classmethod
    def bulk_mark_free(
        cls, timeslot_queryset: TimeSlotQuerySet, remove_appointment_links: bool = False
    ) -> None:
        timeslot_queryset.update(is_available=True)
        if remove_appointment_links:
            time_slot_ids = timeslot_queryset.values_list('id', flat=True)
            TimeSlotToAppointment.objects.filter(time_slot_id__in=time_slot_ids).delete()

    @classmethod
    def bulk_mark_busy(cls, timeslot_queryset: TimeSlotQuerySet) -> None:
        timeslot_queryset.update(is_available=False)

    @classmethod
    def create_from_integration_data(
        cls, create_timeslot_integration_data: CreateTimeSlotIntegrationDict
    ) -> TimeSlot:
        new_timeslot = TimeSlot.objects.create(**create_timeslot_integration_data)
        return new_timeslot

    @classmethod
    def update_from_integration_data(
        cls, timeslot: TimeSlot, update_data: UpdateTimeSlotIntegrationDict
    ) -> TimeSlot:
        timeslot.start = update_data['start']
        timeslot.end = update_data['end']
        integration_data = update_data['integration_data']
        if integration_data and integration_data != timeslot.integration_data:
            timeslot.integration_data = integration_data
        timeslot.save()
        return timeslot

    @classmethod
    def merge_with_nearby_appointment(
        cls, time_slot: TimeSlot, patient: Patient
    ) -> Optional[Appointment]:
        """
        * Найти таймслоты, которые соприкасаются/пересекаются с текущим
        * Взять у этих таймслотов Запись на прием (думаем, что Запись одна)
        * Подлить новый таймслот в найденную Запись
        :return:
        """
        # print('=== merge_with_nearby_appointment')
        new_timeslot = time_slot
        doctor_id = time_slot.doctor_id
        subsidiary_id = time_slot.subsidiary_id

        this_day_doctor_timeslots = (
            DoctorTimeSlots(doctor_id=doctor_id)
            .busy()
            .for_subsidiary(subsidiary_id)
            .start_on_date(time_slot.start_tz.date())
            .order_by('start')
        )
        patient_time_slots = this_day_doctor_timeslots.filter(
            appointments__patient=patient
        ).order_by('start')
        allowed_timedelta = timedelta(minutes=1, seconds=1)
        found_appointment_ids: Set[int] = set()

        for ts in patient_time_slots.iterator():
            ts: TimeSlot
            appointment = ts.first_appointment
            if not appointment:
                continue
            # print(f'=== ts: {ts}')
            # print(f'=== appointment: {appointment}')

            if not all((ts.start, ts.end, new_timeslot.start, new_timeslot.end)):
                err = NoStartEndValuesError("No enough start/end values for merging")
                logging.error(
                    err,
                    extra={
                        "ts": ts,
                        "ts.id": ts.id,
                        "new_timeslot": new_timeslot,
                        "new_timeslot.id": new_timeslot.id,
                    },
                )
                continue
            # from left
            is_old_ts_left = new_timeslot.start > ts.start
            is_old_ts_right = new_timeslot.start < ts.start
            left_delta = new_timeslot.start - ts.end
            right_delta = ts.start - new_timeslot.end
            # print(f"old_ts_left: {old_ts_left}; old_ts_right: {old_ts_right}")
            # print(f"left_delta: {left_delta}; right_delta: {right_delta}")
            if is_old_ts_left and left_delta <= allowed_timedelta:
                # print("---- from left")
                found_appointment_ids.add(appointment.id)

            # from right
            elif is_old_ts_right and right_delta <= allowed_timedelta:
                # print("---- from right")
                found_appointment_ids.add(appointment.id)

        if not found_appointment_ids:
            return

        updated_merged_appointment = None
        if len(found_appointment_ids) > 1:
            with transaction.atomic():
                updated_merged_appointment: Optional[
                    Appointment
                ] = AppointmentWorkflow.merge_nearby_appointments_and_new_timeslot(
                    found_appointment_ids, new_timeslot.id
                )
            if not updated_merged_appointment:
                err = TooManyNearbyAppointments(
                    f'Too many appointments found! Extraordinary case, check it. TimeSlot.id: {time_slot.id}; TimeSlot: {time_slot}'
                )
                logging.exception(
                    err,
                    extra={
                        "time_slot": time_slot,
                        "patient": patient,
                        "patient_time_slot_ids": tuple(
                            patient_time_slots.values_list('id', flat=True)
                        ),
                        "found_appointment_ids": found_appointment_ids,
                    },
                )
                return

        appointment = updated_merged_appointment or AllAppointmentsSelector.get_by_id(
            found_appointment_ids.pop()
        )
        TimeSlotWorkflow.link_with_appointment(time_slot=new_timeslot, appointment=appointment)
        # print(f"----- linked with appointment {appointment}")
        appointment = AppointmentWorkflow.update_start_end_from_linked_timeslots(appointment)
        # print(f"----- finished update_start_end_from_linked_timeslots {appointment}")

        return appointment


time_slot_workflow = TimeSlotWorkflow


class SendEventParamsDictAppointment(TypedDict):
    event_name: str
    user_id: str
    channel: Optional[str]
    appointment_id: int
    context: Dict


class AppointmentNotificationWorkflow:
    validator = AppointmentValidator

    @classmethod
    def _build_send_event_params(
        cls, event_name, appointment, receiver_user_id, **kwargs
    ) -> SendEventParamsDictAppointment:
        """ Аргументы для send_event в одном месте """
        patient = appointment.patient
        patient_user_id = patient.user and patient.user.id
        with_patient_full_name = receiver_user_id != patient_user_id
        event_context = AppointmentUtils.get_event_context_for_appointment_reminder(
            appointment, with_patient_full_name=with_patient_full_name, event_name=event_name
        )

        params = dict(
            event_name=event_name,
            user_id=receiver_user_id,
            channel=PUSH,
            appointment_id=appointment.id,
            context=event_context,
        )
        return params

    @classmethod
    def remind_about_planned_appointment(
        cls,
        appointment: Appointment,
        by_celery_task: bool = False,
        celery_countdown: int = None,
        **kwargs,
    ) -> None:
        """ Appointment must be in "planned" status """
        event_name = kwargs.get('event_name', REMIND_ABOUT_PLANNED_APPOINTMENT)
        cls.validator.check_valid_status(appointment, cls.validator.status_enum.PLANNED)
        patient = appointment.patient
        if not patient.is_confirmed and not appointment.is_created_by_patient:
            return
        user_ids = AppointmentUtils.get_user_ids_to_notify(appointment=appointment)
        for receive_user_id in user_ids:
            send_event_method = send_event
            params = cls._build_send_event_params(
                event_name=event_name, appointment=appointment, receiver_user_id=receive_user_id,
            )
            if by_celery_task:
                send_event_method = send_event.delay
                if celery_countdown:
                    send_event_method = send_event.apply_async
                    params = dict(countdown=celery_countdown, kwargs=params)

            send_event_method(**params)

    @classmethod
    def notify__cancel_by_moderator(cls, appointment: Appointment) -> None:
        cls.validator.check_valid_status(
            appointment, cls.validator.status_enum.CANCELED_BY_MODERATOR
        )
        patient = appointment.patient
        if not patient.is_confirmed and not appointment.is_created_by_patient:
            return

        user_ids = AppointmentUtils.get_user_ids_to_notify(appointment=appointment)
        for user_id in user_ids:
            params = cls._build_send_event_params(
                event_name=APPOINTMENT_CANCELED_BY_ADMIN,
                appointment=appointment,
                receiver_user_id=user_id,
            )
            send_event.delay(**params)

    @classmethod
    def notify__rejected_by_admin(cls, appointment: Appointment) -> None:
        cls.validator.check_valid_status(appointment, cls.validator.status_enum.REJECTED)

        user_ids = AppointmentUtils.get_user_ids_to_notify(appointment=appointment)
        for user_id in user_ids:
            params = cls._build_send_event_params(
                event_name=APPOINTMENT_REQUEST__REJECTED_BY_ADMIN,
                appointment=appointment,
                receiver_user_id=user_id,
            )
            send_event.delay(**params)

    @classmethod
    def notify__approved_by_moderator(cls, appointment: Appointment) -> None:
        cls.validator.check_valid_status(appointment, cls.validator.status_enum.PLANNED)

        user_ids = AppointmentUtils.get_user_ids_to_notify(appointment=appointment)
        for user_id in user_ids:
            params = cls._build_send_event_params(
                event_name=APPOINTMENT_REQUEST__APPROVED_BY_ADMIN,
                appointment=appointment,
                receiver_user_id=user_id,
            )
            send_event.delay(**params)
