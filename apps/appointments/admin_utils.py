from django.contrib.admin import SimpleListFilter
from django.db.models import Q
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

from apps.appointments.models import Appointment
from apps.clinics.admin_tools import get_patient_href
from apps.core.admin import get_change_href
from apps.profiles.admin_utils import get_profile_links_as_common_str


def get_timeslot_links(appointment: Appointment, start_string=None):
    if not appointment.has_timeslots:
        return

    links = ""
    if start_string:
        links = start_string + "<br />"

    timeslots = appointment.time_slots.all()
    for timeslot in timeslots.iterator():
        links += f"> {get_change_href(timeslot, label=timeslot.short_str)}<br />"

    return format_html(links)


def get_patient_links(appointment: Appointment, start_string=None, with_contacts=False) -> str:
    if not appointment.patient_id:
        return ''
    patient = appointment.patient
    links = f"> {get_patient_href(patient, label=f'пациент - {patient.short_full_name}')}<br />"

    if patient.profile:
        profile_links = get_profile_links_as_common_str(
            patient.profile, start_string=None, with_contacts=with_contacts
        )
        links += profile_links
    return format_html(links)


class TimeSlotHasAppointmentFilterFilter(SimpleListFilter):
    title = _('Есть ли связь с Записями?')  # a label for our filter
    parameter_name = 'has_appointment_link'  # you can put anything here

    def lookups(self, request, model_admin):
        # This is where you create filter options; we have two:
        return [
            ('yes', _('Да')),
            ('no', _('Нет')),
        ]

    def queryset(self, request, queryset):
        # This is where you process parameters selected by use via filter options:
        with_appointments_q = Q(appointments__isnull=False)
        if self.value() == 'yes':
            # Get websites that have at least one page.
            return queryset.filter(with_appointments_q)
        elif self.value() == "no":
            # Get websites that don't have any pages.
            return queryset.exclude(with_appointments_q)
        return queryset


class AppointmentsWithRegisteredUsersFilter(SimpleListFilter):
    title = _('Только пациенты с приложением?')  # a label for our filter
    parameter_name = 'only_patients_with_users'  # you can put anything here

    def lookups(self, request, model_admin):
        # This is where you create filter options; we have two:
        return [
            ('yes', _('Да')),
            ('no', _('Нет')),
        ]

    def queryset(self, request, queryset):
        # This is where you process parameters selected by use via filter options:
        with_user_q = Q(patient__profile__users__isnull=False)
        if self.value() == 'yes':
            # Get websites that have at least one page.
            return queryset.filter(with_user_q)
        elif self.value() == "no":
            # Get websites that don't have any pages.
            return queryset.exclude(with_user_q)
        return queryset
