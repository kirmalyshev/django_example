from typing import Optional

from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from apps.appointments.constants import AUTHOR_PATIENT, APPOINTMENT_ID, APPOINTMENT, DOCTOR, SERVICE
from apps.core.admin import DisplayableAdmin, get_change_href
from apps.core.constants import CREATED, MODIFIED
from apps.feature_toggles.ops_features import is_reviews_enabled
from apps.reviews.admin_tools import HasTextFilter
from apps.reviews.constants import GRADE
from apps.reviews.models import Review


@admin.register(Review)
class ReviewAdmin(DisplayableAdmin):
    date_hierarchy = CREATED
    list_display = (
        'id',
        GRADE,
        'short_text',
        'get_appointment_patient_link',
        'doctor',
        'get_doctor_link',
        'get_appointment_link',
        'status',
        'is_displayed',
        CREATED,
    )
    list_display_links = (
        'id',
        GRADE,
        'short_text',
    )
    list_filter = (
        GRADE,
        HasTextFilter,
        'status',
        CREATED,
        'is_displayed',
    )
    search_fields = (
        'id',
        f'{AUTHOR_PATIENT}__profile__full_name',
        f'{AUTHOR_PATIENT}__profile__users__username',
        f'{AUTHOR_PATIENT}__profile__users__contacts__value',
        'text',
        f'{DOCTOR}__profile__full_name',
        f'{DOCTOR}__public_full_name',
        f'{DOCTOR}__public_short_name',
        APPOINTMENT_ID,
        'appointment__id',
    )
    readonly_fields = (
        CREATED,
        MODIFIED,
        "id",
        'get_appointment_patient_link',
        'get_doctor_link',
        'get_appointment_link',
    )
    raw_id_fields = (
        APPOINTMENT,
        AUTHOR_PATIENT,
        DOCTOR,
    )
    autocomplete_fields = (DOCTOR, AUTHOR_PATIENT)
    list_select_related = (
        APPOINTMENT,
        AUTHOR_PATIENT,
        f'{AUTHOR_PATIENT}__profile',
        DOCTOR,
        f'{DOCTOR}__profile',
        SERVICE,
    )
    fieldsets = (
        (_("Модерация"), {'fields': ('id', 'status', 'is_displayed',)}),
        (
            _("Общее"),
            {
                'fields': (
                    GRADE,
                    'text',
                    AUTHOR_PATIENT,
                    'get_appointment_patient_link',
                    'get_doctor_link',
                    'get_appointment_link',
                )
            },
        ),
        (_('Внутренняя информация'), {'fields': (CREATED, MODIFIED,)},),
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        qs = super(ReviewAdmin, self).get_queryset(request)
        return qs.prefetch_related(f'{AUTHOR_PATIENT}__profile',)

    def get_appointment_link(self, obj: Review) -> Optional[str]:
        if not obj.appointment_id:
            return
        appointment = obj.appointment
        return get_change_href(appointment, label=f'Запись')

    get_appointment_link.short_description = _('запись')
    get_appointment_link.allow_tags = True

    def get_appointment_patient_link(self, obj: Review) -> Optional[str]:
        if not obj.appointment_id:
            return
        patient = obj.appointment.patient
        return get_change_href(patient, label=f'{patient.short_full_name}')

    get_appointment_patient_link.short_description = _('пациент')
    get_appointment_patient_link.allow_tags = True

    def get_doctor_link(self, obj: Review) -> Optional[str]:
        if not obj.doctor_id:
            return
        doctor = obj.doctor
        return get_change_href(doctor, label=f'{doctor.short_full_name}')

    get_doctor_link.short_description = _('доктор (ссылка)')
    get_doctor_link.allow_tags = True


if not is_reviews_enabled.is_enabled:
    admin.site.unregister(Review)
