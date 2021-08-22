from typing import Final

from django.utils.translation import ugettext_lazy as _

PATIENT = "patient"

DOCTOR_STR = _('врач')
SUBSIDIARY_STR = _('филиал')

IMPORT_PRICES = "import_prices"


class DoctorStatus:
    DELETED = 'deleted'
    WORKING = 'working'
    ON_VACATION = 'on_vacation'
    FIRED = 'fired'

    CHOICES = (
        (WORKING, _('работает')),
        (ON_VACATION, _('в отпуске')),
        (FIRED, _('уволен/уволился')),
        (DELETED, _('удален')),
    )


class StaffStatus:
    WORKING = 'working'
    ON_VACATION = 'on_vacation'
    FIRED = 'fired'

    CHOICES = (
        (WORKING, _('работает')),
        (ON_VACATION, _('в отпуске')),
        (FIRED, _('уволен/уволился')),
    )


I_NEED_CONSULTATION = "Мне нужна консультация"

ONLY_ROOT = "only_root"
PARENT_ID: Final[str] = "parent_id"
INTEGRATION_DATA: Final[str] = 'integration_data'
SPECIALITY_TEXT: Final = "speciality_text"


class MobileAppSections:
    SERVICES = "services"
    DOCTORS = "doctors"
    CREATE_APPOINTMENT_BY_PATIENT = "create_appointment_by_patient"

    VALUES = (SERVICES, DOCTORS, CREATE_APPOINTMENT_BY_PATIENT)
