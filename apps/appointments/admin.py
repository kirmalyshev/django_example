from django.contrib import admin, messages
from django.contrib.admin.templatetags.admin_urls import add_preserved_filters
from django.core.exceptions import ValidationError
from django.http import HttpRequest
from django.shortcuts import redirect
from django.urls import reverse, path
from django.utils.encoding import force_text
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

from apps.appointments import models
from apps.appointments.admin_utils import (
    get_timeslot_links,
    get_patient_links,
    TimeSlotHasAppointmentFilterFilter,
    AppointmentsWithRegisteredUsersFilter,
)
from apps.appointments.constants import (
    IS_FOR_WHOLE_DAY,
    ADDITIONAL_NOTES,
    SUBSIDIARY,
    START,
    END,
    DOCTOR,
    SERVICE,
    HUMAN_START,
    AUTHOR_PATIENT,
    PRICE,
    REASON_TEXT,
)
from apps.appointments.exceptions import AppointmentError
from apps.appointments.managers import AppointmentQuerySet
from apps.appointments.models import Appointment
from apps.appointments.workflows import AppointmentModerationWorkflow, AppointmentWorkflow
from apps.clinics.constants import PATIENT, INTEGRATION_DATA
from apps.core.admin import (
    BUTTON_TEMPLATE,
    BaseProcessActionsAdminMixin,
    ReadOnlyAdminMixin,
)
from apps.reviews.models import Review
from apps.reviews.tools import is_adding_review_allowed
from apps.reviews.workflow import ReviewWorkflow
from apps.core.constants import CREATED, MODIFIED
from apps.tools.easyaudit_history_admin import CRUDHistoryMixin


class TimeSlotToAppointmentInline(admin.StackedInline):
    model = models.TimeSlotToAppointment
    raw_id_fields = ('time_slot',)


class BaseAppointmentAdmin(CRUDHistoryMixin, admin.ModelAdmin):
    list_display = (
        'id',
        PATIENT,
        AUTHOR_PATIENT,
        START,
        'duration',
        DOCTOR,
        SUBSIDIARY,
        'status',
        'moderation_actions',
        'get_patient_links',
        'get_timeslot_links',
        # "crud_history_link",
        CREATED,
        MODIFIED,
    )
    list_display_links = (
        'id',
        PATIENT,
    )
    raw_id_fields = (
        PATIENT,
        AUTHOR_PATIENT,
        SERVICE,
        DOCTOR,
    )

    list_filter = (
        CREATED,
        MODIFIED,
        AppointmentsWithRegisteredUsersFilter,
        'status',
        START,
        IS_FOR_WHOLE_DAY,
        'created_by_type',
        # 'doctor',
        # SERVICE,
        SUBSIDIARY,
    )
    search_fields = (
        'id',
        f'{AUTHOR_PATIENT}__profile__full_name',
        f'{AUTHOR_PATIENT}__profile__users__username',
        f'{AUTHOR_PATIENT}__profile__users__contacts__value',
        f'{PATIENT}__profile__full_name',
        f'{PATIENT}__profile__users__username',
        f'{PATIENT}__profile__users__contacts__value',
        REASON_TEXT,
        f'{DOCTOR}__profile__full_name',
        f'{DOCTOR}__public_full_name',
        f'{DOCTOR}__public_short_name',
        INTEGRATION_DATA,
    )
    readonly_fields = (
        'duration',
        INTEGRATION_DATA,
        'get_timeslot_links',
        'get_patient_links',
        CREATED,
        MODIFIED,
        HUMAN_START,
    )

    list_select_related = (
        PATIENT,
        AUTHOR_PATIENT,
        f"{AUTHOR_PATIENT}__profile",
        f'{PATIENT}__profile',
        DOCTOR,
        f'{DOCTOR}__profile',
        SUBSIDIARY,
        SERVICE,
    )

    autocomplete_fields = (SERVICE, DOCTOR, PATIENT, AUTHOR_PATIENT, SUBSIDIARY)

    actions = ("mark_finished_action",)

    def get_queryset(self, request):
        queryset = super(BaseAppointmentAdmin, self).get_queryset(request)
        return queryset.select_related(*self.list_select_related).prefetch_related(
            f"{PATIENT}__profile",
            f"{PATIENT}__profile__users",
            f"{PATIENT}__profile__users__contacts",
            f"{AUTHOR_PATIENT}__profile",
            f"{AUTHOR_PATIENT}__profile__users",
            f"{AUTHOR_PATIENT}__profile__users__contacts",
            'time_slots',
        )

    def get_patient_links(self, obj: models.Appointment):
        return get_patient_links(obj)

    get_patient_links.short_description = _('ссылки')
    get_patient_links.allow_tags = True

    def get_timeslot_links(self, obj: models.Appointment):
        return get_timeslot_links(obj)

    get_timeslot_links.short_description = _('Талоны')
    get_timeslot_links.allow_tags = True

    def mark_finished_action(self, request, queryset: AppointmentQuerySet):
        for appointment in queryset.iterator():
            AppointmentWorkflow.finish(appointment)

    mark_finished_action.short_description = _('Пометить как Завершенные')

    def human_start(self, obj: models.Appointment):
        return obj.human_start_tz

    human_start.short_description = _('дата/время начала в человеческом виде')
    human_start.allow_tags = True


@admin.register(models.AppointmentResult)
class AppointmentResultAdmin(admin.ModelAdmin):
    raw_id_fields = ('appointment',)


class AppointmentResultInline(admin.TabularInline):
    model = models.AppointmentResult


class AppointmentReviewReadOnlyInline(admin.TabularInline):
    model = Review
    show_change_link = True
    extra = 1
    autocomplete_fields = (AUTHOR_PATIENT, "doctor")

    def has_add_permission(self, request, obj=None):
        return False


class AppointmentModerationMixin(BaseProcessActionsAdminMixin, admin.ModelAdmin):
    moderation_workflow = AppointmentModerationWorkflow

    def get_action_methods(self):
        methods = super(AppointmentModerationMixin, self).get_action_methods()
        methods.update(
            {
                'approve': self.approve_action,
                'reject': self.reject_action,
                'back_to_moderation': self.back_to_moderation_action,
                "ask_for_review": self.ask_for_review_action,
            }
        )
        return methods

    def approve_view(self, request: HttpRequest, object_id: int):
        return self.process_action(request, object_id, 'approve')

    def reject_view(self, request: HttpRequest, object_id: int):
        return self.process_action(request, object_id, 'reject')

    def back_to_moderation_view(self, request: HttpRequest, object_id: int):
        return self.process_action(request, object_id, 'back_to_moderation')

    def ask_for_review_view(self, request: HttpRequest, object_id: int):
        return self.process_action(request, object_id, 'ask_for_review')

    def get_urls(self):
        urls = super(AppointmentModerationMixin, self).get_urls()
        info = self._get_path_info()
        moderation_urls = [
            path(
                '<path:object_id>/reject/',
                self.admin_site.admin_view(self.reject_view),
                name='%s_%s_reject' % info,
            ),
            path(
                '<path:object_id>/approve/',
                self.admin_site.admin_view(self.approve_view),
                name='%s_%s_approve' % info,
            ),
            path(
                '<path:object_id>/back_to_moderation/',
                self.admin_site.admin_view(self.back_to_moderation_view),
                name='%s_%s_back_to_moderation' % info,
            ),
            path(
                '<path:object_id>/ask_for_review/',
                self.admin_site.admin_view(self.ask_for_review_view),
                name='%s_%s_ask_for_review' % info,
            ),
        ]
        return moderation_urls + urls

    def reject_action(self, request: HttpRequest, obj: Appointment):
        try:
            self.moderation_workflow.reject_by_moderator(obj)
            msg_status = messages.SUCCESS
            model_name = force_text(self.model._meta.verbose_name)
            msg = _(f'{model_name} отклонена.')
        except AppointmentError as err:
            msg_status = messages.ERROR
            msg = '. '.join((str(err.title), str(err.details or '')))
        except ValidationError as err:
            msg_status = messages.ERROR
            msg = err.message

        self.message_user(request, msg, msg_status)
        return redirect(self.get_redirect_url__to_referer(request))

    reject_action.short_description = _('Отклонить')

    def approve_action(self, request: HttpRequest, obj: Appointment):
        try:
            self.moderation_workflow.approve(obj)
            msg_status = messages.SUCCESS
            model_name = force_text(self.model._meta.verbose_name)
            msg = _(f'{model_name} одобрена.')
        except AppointmentError as err:
            msg_status = messages.ERROR
            msg = '. '.join((str(err.title), str(err.details or '')))
        except ValidationError as err:
            msg_status = messages.ERROR
            msg = err.message

        self.message_user(request, msg, msg_status)
        return redirect(self.get_redirect_url__to_referer(request))

    approve_action.short_description = _('Одобрить')

    def back_to_moderation_action(self, request: HttpRequest, obj: Appointment):
        try:
            self.moderation_workflow.return_to_moderation(obj)
            msg_status = messages.SUCCESS
            model_name = force_text(self.model._meta.verbose_name)
            msg = _(f'{model_name} возвращен(а) на модерацию.')
        except AppointmentError as err:
            msg_status = messages.ERROR
            msg = '. '.join((str(err.title), str(err.details or '')))
        except ValidationError as err:
            msg_status = messages.ERROR
            msg = err.message

        self.message_user(request, msg, msg_status)
        return redirect(self.get_redirect_url__to_referer(request))

    back_to_moderation_action.short_description = _('На модерацию')

    def ask_for_review_action(self, request: HttpRequest, obj: Appointment):
        try:
            ReviewWorkflow.ask_for_appointment_review(appointment=obj)
            msg_status = messages.SUCCESS
            model_name = force_text(self.model._meta.verbose_name)
            msg = _(f'Запрошен отзыв от пользователя -- {obj} ')
        except ValidationError as err:
            msg_status = messages.ERROR
            msg = err.message
        except Exception as err:
            msg_status = messages.ERROR
            msg = '. '.join((str(err.title), str(err.details or '')))

        self.message_user(request, msg, msg_status)
        return redirect(self.get_redirect_url__to_referer(request))

    def response_change(self, request, obj):
        """
        Determines the HttpResponse for the change_view stage.
        Support for _reject_appointment and _approve_appointment submit actions.
        """
        has_reject = '_reject_appointment' in request.POST
        has_approve = '_approve_appointment' in request.POST

        if not any((has_reject, has_approve)):
            return super(AppointmentModerationMixin, self).response_change(request, obj)

        target_url = request.path
        opts = self.model._meta
        if has_reject:
            self.reject_action(request, obj)
        elif has_approve:
            self.approve_action(request, obj)

        preserved_filters = self.get_preserved_filters(request)
        redirect_url = add_preserved_filters(
            {'preserved_filters': preserved_filters, 'opts': opts}, target_url
        )

        return redirect(redirect_url)

    REJECT_BUTTON = BUTTON_TEMPLATE.format(
        url="{reject_url}",
        title='Отклонить',
        style='background: #D42700; color: white; border-width: 2px; font-weight: bold',
    )
    APPROVE_BUTTON = BUTTON_TEMPLATE.format(
        url='{approve_url}',
        title='Одобрить',
        style='background: green; color: white; border-width: 2px; font-weight: bold',
    )
    BACK_TO_MODERATION_BUTTON = BUTTON_TEMPLATE.format(
        url='{back_to_moderation_url}',
        title='Вернуть на модерацию',
        style='background: blue; color: white; border-width: 2px; font-weight: bold',
    )
    ASK_FOR_REVIEW_BUTTON = BUTTON_TEMPLATE.format(
        url='{ask_for_review_url}',
        title='Запросить отзыв',
        style='background: dark-blue; color: white; border-width: 2px; font-weight: bold',
    )

    def _get_approve_url(self, obj: Appointment):
        info = self._get_path_info()
        return reverse('admin:%s_%s_approve' % info, args=[obj.pk])

    def _get_reject_url(self, obj: Appointment):
        info = self._get_path_info()
        return reverse('admin:%s_%s_reject' % info, args=[obj.pk])

    def _get_back_to_moderation_url(self, obj: Appointment):
        info = self._get_path_info()
        return reverse('admin:%s_%s_back_to_moderation' % info, args=[obj.pk])

    def _get_ask_for_review_url(self, obj: Appointment):
        info = self._get_path_info()
        return reverse('admin:%s_%s_ask_for_review' % info, args=[obj.pk])

    def moderation_actions(self, obj: Appointment):
        buttons = set()
        if obj.is_on_moderation:
            buttons.add(self.REJECT_BUTTON)
            buttons.add(self.APPROVE_BUTTON)
        if obj.is_rejected or obj.is_planned:
            buttons.add(self.BACK_TO_MODERATION_BUTTON)
        if is_adding_review_allowed(obj):
            buttons.add(self.ASK_FOR_REVIEW_BUTTON)

        return format_html(
            '<br><br>'.join(buttons),
            reject_url=self._get_reject_url(obj),
            approve_url=self._get_approve_url(obj),
            back_to_moderation_url=self._get_back_to_moderation_url(obj),
            ask_for_review_url=self._get_ask_for_review_url(obj),
        )

    moderation_actions.short_description = _('действия')
    moderation_actions.allow_tags = True


@admin.register(models.Appointment)
class AppointmentAdmin(BaseAppointmentAdmin, AppointmentModerationMixin):
    list_display = (
        'id',
        PATIENT,
        AUTHOR_PATIENT,
        START,
        'duration',
        DOCTOR,
        SUBSIDIARY,
        'status',
        'moderation_actions',
        'get_patient_links',
        INTEGRATION_DATA,
        'get_timeslot_links',
        "crud_history_link",
        CREATED,
        MODIFIED,
    )
    readonly_fields = (
        'get_patient_links',
        'duration',
        INTEGRATION_DATA,
        'moderation_actions',
        REASON_TEXT,
        'get_timeslot_links',
        CREATED,
        MODIFIED,
        HUMAN_START,
    )
    fieldsets = (
        (
            None,
            {
                'fields': (
                    PATIENT,
                    'get_patient_links',
                    START,
                    END,
                    'duration',
                    REASON_TEXT,
                    DOCTOR,
                    SERVICE,
                    SUBSIDIARY,
                    PRICE,
                    IS_FOR_WHOLE_DAY,
                    HUMAN_START,
                    ADDITIONAL_NOTES,
                )
            },
        ),
        (
            _('Внутренняя информация'),
            {
                'fields': (
                    'created_by_type',
                    AUTHOR_PATIENT,
                    'status',
                    INTEGRATION_DATA,
                    CREATED,
                    MODIFIED,
                )
            },
        ),
    )
    inlines = (
        TimeSlotToAppointmentInline,
        AppointmentResultInline,
        AppointmentReviewReadOnlyInline,
    )


@admin.register(models.AppointmentOnModeration)
class AppointmentOnModerationAdmin(
    BaseAppointmentAdmin, AppointmentModerationMixin, ReadOnlyAdminMixin
):
    list_filter = (
        CREATED,
        MODIFIED,
        START,
        DOCTOR,
        SERVICE,
        SUBSIDIARY,
    )


@admin.register(models.PlannedAppointment)
class PlannedAppointmentAdmin(BaseAppointmentAdmin, AppointmentModerationMixin, ReadOnlyAdminMixin):
    def has_add_permission(self, request):
        return False

    ordering = ('start',)


@admin.register(models.ArchivedAppointment)
class ArchivedAppointmentAdmin(AppointmentAdmin, ReadOnlyAdminMixin):
    def has_add_permission(self, request):
        return False


@admin.register(models.TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        START,
        'duration',
        END,
        DOCTOR,
        SUBSIDIARY,
        'is_available',
        INTEGRATION_DATA,
        CREATED,
        MODIFIED,
    )
    date_hierarchy = START
    list_display_links = (
        'id',
        START,
    )
    list_filter = (
        TimeSlotHasAppointmentFilterFilter,
        START,
        CREATED,
        MODIFIED,
        SUBSIDIARY,
        'is_available',
        DOCTOR,
    )
    list_select_related = (
        DOCTOR,
        'doctor__profile',
        SUBSIDIARY,
    )
    raw_id_fields = (DOCTOR,)
    readonly_fields = (
        'duration',
        'is_available',
        'appointments',
        INTEGRATION_DATA,
        CREATED,
        MODIFIED,
    )
    search_fields = (
        'id',
        'doctor__speciality_text',
        'doctor__profile__full_name',
        'doctor__public_full_name',
        'doctor__public_short_name',
        'subsidiary__title',
        'subsidiary__address',
        'doctor__services__title',
        INTEGRATION_DATA,
    )

    fieldsets = (
        (None, {'fields': (START, END, 'duration')},),
        (_('Чей слот'), {'fields': (DOCTOR, SUBSIDIARY)}),
        (
            _('Внутренняя информация'),
            {'fields': ('is_available', 'appointments', INTEGRATION_DATA, CREATED, MODIFIED,)},
        ),
    )

    def get_queryset(self, request):
        qs = self.model.all_objects.get_queryset()
        ordering = self.get_ordering(request)
        if ordering:
            qs = qs.order_by(*ordering)
        return qs


@admin.register(models.FutureTimeSlot)
class FutureTimeSlotAdmin(TimeSlotAdmin):
    pass


@admin.register(models.TimeSlotToAppointment)
class TimeSlotToAppointmentAdmin(admin.ModelAdmin, ReadOnlyAdminMixin):
    pass
