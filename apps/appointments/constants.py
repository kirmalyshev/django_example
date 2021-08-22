from datetime import timedelta, datetime
from typing import Optional, TypedDict, List, Final, Union

from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from apps.core.constants import BaseStatus

MIN_APPOINTMENT_TIMEDELTA = timedelta(seconds=0)
MAX_APPOINTMENT_TIMEDELTA = timedelta(hours=24)
MIN_TIMESLOT_TIMEDELTA = timedelta(seconds=1)
MAX_TIMESLOT_TIMEDELTA = timedelta(hours=24)

APPOINTMENT_DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S'


class AppointmentStatus(BaseStatus):
    HIDDEN = 0
    ON_MODERATION = 1
    REJECTED = 2
    # APPROVED = 3
    PLANNED = 10
    CANCELED_BY_MODERATOR = 20
    CANCELED_BY_PATIENT = 21
    CANCELED_BY_DOCTOR = 22
    CANCEL_REQUEST_BY_PATIENT = 23
    PATIENT_ARRIVED = 30
    ON_APPOINTMENT = 40
    AWAITING_PAYMENT = 50
    FINISHED = 60
    MISSED = 70

    VALUES = {
        HIDDEN: _('спрятана'),
        ON_MODERATION: _('на модерации'),
        REJECTED: _('отклонена'),
        # APPROVED: _('одобрена'),
        PLANNED: _('запланирована'),
        CANCELED_BY_MODERATOR: _('отменен администратором'),
        CANCEL_REQUEST_BY_PATIENT: _('запрос на отмену от пациента'),
        CANCELED_BY_PATIENT: _('отменен пациентом'),
        CANCELED_BY_DOCTOR: _('отменен доктором'),
        PATIENT_ARRIVED: _('пациент пришел'),
        ON_APPOINTMENT: _('на приеме'),
        AWAITING_PAYMENT: _('приём окончен, требуется оплата'),
        FINISHED: _('прием завершен'),
        MISSED: _('прием не состоялся'),
    }
    VALUE_KEYS = VALUES.keys()

    CHOICES = VALUES.items()

    VISIBLE_FOR_PATIENT = (
        ON_MODERATION,
        REJECTED,
        PLANNED,
        CANCELED_BY_MODERATOR,
        CANCEL_REQUEST_BY_PATIENT,
        # CANCELED_BY_PATIENT,
        CANCELED_BY_DOCTOR,
        PATIENT_ARRIVED,
        ON_APPOINTMENT,
        AWAITING_PAYMENT,
        FINISHED,
    )
    VISIBLE_BY_PATIENT__ACTIVE = (
        ON_MODERATION,
        PLANNED,
        PATIENT_ARRIVED,
        ON_APPOINTMENT,
        AWAITING_PAYMENT,
        CANCEL_REQUEST_BY_PATIENT,
    )

    ARCHIVED = (
        REJECTED,
        # APPROVED,
        CANCELED_BY_MODERATOR,
        CANCELED_BY_PATIENT,
        CANCELED_BY_DOCTOR,
        FINISHED,
        MISSED,
    )
    VISIBLE_BY_PATIENT__ARCHIVED = (
        # REJECTED,
        # APPROVED,
        CANCELED_BY_MODERATOR,
        # Не показываем те, что пациент сам отменил, чтоб не захламлять историю в приложении
        # CANCELED_BY_PATIENT,
        CANCELED_BY_DOCTOR,
        FINISHED,
    )

    AVAILABLE_TO_CANCEL_BY_PATIENT = (PLANNED,)
    if settings.INTEGRATION__ALLOW_CANCEL_APPOINTMENT_REQUEST:
        AVAILABLE_TO_CANCEL_BY_PATIENT = (
            ON_MODERATION,
            PLANNED,
        )
    CANCELED_VALUES = (CANCELED_BY_DOCTOR, CANCELED_BY_MODERATOR, CANCELED_BY_PATIENT)


ONLY_FUTURE = 'only_future'
ONLY_PAST = 'only_past'
ONLY_ACTIVE = 'only_active'
ONLY_ARCHIVED = 'only_archived'
DOCTOR = "doctor"
DOCTOR_ID = "doctor_id"
PATIENT_ID = "patient_id"
AUTHOR_PATIENT: Final = "author_patient"
TARGET_PATIENT: Final = "target_patient"
TARGET_PATIENT_ID: Final = "target_patient_id"
SERVICE: Final = 'service'
SERVICE_ID: Final = 'service_id'
SUBSIDIARY = 'subsidiary'
SUBSIDIARY_ID = 'subsidiary_id'
START = 'start'
HUMAN_START: Final = "human_start"
HUMAN_WEEKDAY: Final = "human_weekday"
HUMAN_START_TIME: Final = "human_start_time"
HUMAN_START_DATE: Final = "human_start_date"
HUMAN_START_DATETIME: Final = "human_start_datetime"
HUMAN_START_DATE_SHORT: Final = "human_start_date_short"
END = 'end'
TIME_SLOT_ID = "time_slot_id"
APPOINTMENT: Final = "appointment"
APPOINTMENT_ID: Final = "appointment_id"
APPOINTMENT_REQUEST_ID: Final = "appointment_request_id"
TIMESLOT_ID: Final = "timeslot_id"
RELATED_PATIENT_FULL_NAME = "related_patient_full_name"
ADDITIONAL_NOTES: Final = "additional_notes"
IS_FOR_WHOLE_DAY: Final = "is_for_whole_day"
REASON_TEXT: Final = "reason_text"
EMPTY_REASON_TEXT: Final = "Пустая заявка"
PRICE: Final = "price"
CREATED_BY_TYPE: Final = "created_by_type"

# region Event names
REMIND_ABOUT_PLANNED_APPOINTMENT = "remind_about_planned_appointment"
APPOINTMENT_CANCELED_BY_ADMIN = "appointment_canceled_by_admin"
APPOINTMENT_CREATED_BY_ADMIN = "appointment_created_by_admin"
APPOINTMENT_REQUEST__REJECTED_BY_ADMIN = "appointment_request__rejected_by_admin"
APPOINTMENT_REQUEST__APPROVED_BY_ADMIN = "appointment_request__approved_by_admin"
APPOINTMENT__ASK_FOR_REVIEW: Final = "appointment__ask_for_review"
# endregion

# region mobile app action names
ADD_APPOINMENT_REVIEW = "add_appointment_review"
# endregion

# region Notification template constants
APPOINTMENT_START = "appointment_start"
SUBSIDIARY_ADDRESS = "subsidiary_address"
DOCTOR_FULL_NAME = "doctor_full_name"
APPOINTMENT_STR_FOR_PATIENT = "appointment_str_for_patient"
PATIENT_FULL_NAME = "patient_full_name"


# end


class TimeSlotIntegrationData(TypedDict):
    timeslot_id: int


class CreateTimeSlotIntegrationDict(TypedDict):
    subsidiary_id: int
    doctor_id: int
    start: Optional[datetime]
    end: Optional[datetime]
    is_available: Optional[bool]
    integration_data: Optional[TimeSlotIntegrationData]


class UpdateTimeSlotIntegrationDict(TypedDict):
    doctor_id: int
    start: Optional[datetime]
    end: Optional[datetime]
    is_available: Optional[bool]
    integration_data: Optional[TimeSlotIntegrationData]


class AppointmentExtraSubsidiaryInfoDict(TypedDict):
    subsidiary_id: int
    talon_id: Optional[int]
    appointment_request_id: Optional[int]


class AppointmentIntegrationDataDict(TypedDict):
    extra_subsidiary_info: List[AppointmentExtraSubsidiaryInfoDict]


class CreateAppointmentByPatientDict(TypedDict):
    time_slot_id: Optional[int]
    subsidiary_id: Optional[int]
    service_id: Optional[int]
    doctor_id: Optional[int]
    reason_text: Optional[str]
    start: Optional[datetime]
    end: Optional[datetime]

    target_patient_id: Optional[int]
    author_patient: Union[
        int,
    ]


class CreateAppointmentDict(TypedDict):
    subsidiary_id: int
    service_id: Optional[int]
    patient_id: int
    doctor_id: int
    start: Optional[datetime]
    end: Optional[datetime]
    status: int
    integration_data: Optional[AppointmentIntegrationDataDict]
    created_by_type: Optional[str]


class UpdateAppointmentDict(TypedDict):
    subsidiary_id: int
    service_id: Optional[int]
    patient_id: int
    doctor_id: int
    start: Optional[datetime]
    end: Optional[datetime]
    status: int
    integration_data: Optional[AppointmentIntegrationDataDict]


class AppointmentCreatedValues:
    PATIENT = "patient"
    DOCTOR = "doctor"
    ADMINISTRATOR = "administrator"

    VALUES = {
        PATIENT: _('пациент'),
        DOCTOR: _('доктор'),
        ADMINISTRATOR: _('администратор'),
    }

    VALUE_KEYS = VALUES.keys()

    CHOICES = VALUES.items()


class DefaultNotes:
    DURING_ALL_DAY = _("в течение дня")
