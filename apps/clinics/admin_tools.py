import logging

from django.contrib import messages, admin
from django.contrib.admin import SimpleListFilter
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.http import HttpRequest
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

from apps.clinics.models import Patient
from apps.clinics.tools import get_patient_related_object_ids
from apps.clinics.workflows import PatientWorkflow
from apps.core.admin import get_change_href, BaseProcessActionsAdminMixin
from apps.tools.easyaudit_history_admin import CRUDHistoryMixin


def get_patient_href(patient: Patient, label="") -> str:
    if not label:
        label = f'пациент - {patient.short_full_name}'
    return get_change_href(patient, label=label)


class HasProfilePhotoFilter(SimpleListFilter):
    title = _('Есть ли фото профиля?')  # a label for our filter
    parameter_name = 'has_profile_photo'  # you can put anything here

    def lookups(self, request, model_admin):
        # This is where you create filter options; we have two:
        return [
            ('yes', _('Да')),
            ('no', _('Нет')),
        ]

    def queryset(self, request, queryset):
        # This is where you process parameters selected by use via filter options:
        no_photos_q = Q(Q(profile__picture_draft__isnull=True) | Q(profile__picture_draft=''))
        if self.value() == 'yes':
            # Get websites that have at least one page.
            return queryset.exclude(no_photos_q)
        if self.value():
            # Get websites that don't have any pages.
            return queryset.filter(no_photos_q)


class DoctorHasEducationFilter(SimpleListFilter):
    title = _('Заполнено Образование?')  # a label for our filter
    parameter_name = 'has_education'  # you can put anything here

    def lookups(self, request, model_admin):
        # This is where you create filter options; we have two:
        return [
            ('yes', _('Да')),
            ('no', _('Нет')),
        ]

    def queryset(self, request, queryset):
        # This is where you process parameters selected by use via filter options:
        no_education_q = Q(Q(education__isnull=True) | Q(education=''))
        if self.value() == 'yes':
            # Get websites that have at least one page.
            return queryset.exclude(no_education_q)
        if self.value():
            # Get websites that don't have any pages.
            return queryset.filter(no_education_q)


class DoctorHasYoutubeVideoFilter(SimpleListFilter):
    title = _('Есть видеовизитка?')  # a label for our filter
    parameter_name = 'has_youtube_video'  # you can put anything here

    def lookups(self, request, model_admin):
        # This is where you create filter options; we have two:
        return [
            ('yes', _('Да')),
            ('no', _('Нет')),
        ]

    def queryset(self, request, queryset):
        # This is where you process parameters selected by use via filter options:
        no_youtube_link_q = Q(Q(youtube_video_link__isnull=True) | Q(youtube_video_link=''))
        if self.value() == 'yes':
            # Get websites that have at least one page.
            return queryset.exclude(no_youtube_link_q)
        if self.value():
            # Get websites that don't have any pages.
            return queryset.filter(no_youtube_link_q)


class PatientHasUserFilter(SimpleListFilter):
    title = _('Есть ли юзер?')  # a label for our filter
    parameter_name = 'has_user'  # you can put anything here

    def lookups(self, request, model_admin):
        # This is where you create filter options; we have two:
        return [
            ('yes', _('Да')),
            ('no', _('Нет')),
            ('all', _('все')),
        ]

    def queryset(self, request, queryset):
        # This is where you process parameters selected by use via filter options:
        with_user_q = Q(profile__users__isnull=False)
        value = self.value()
        if value == 'yes':
            # Get websites that have at least one page.
            return queryset.filter(with_user_q)
        elif value == "no":
            # Get websites that don't have any pages.
            return queryset.exclude(with_user_q)
        elif value == "all":
            return queryset


class MergePatientsAdminMixin:
    actions = ("merge_selected_patients",)

    def merge_patients_message_error(self, msg_text: str, request: HttpRequest):
        msg_status = messages.ERROR
        msg = format_html(f"Невозможно объединить пациентов:<br/>{msg_text}")
        self.message_user(request, msg, msg_status)

    def merge_patients_message_success(self, msg_text: str, request: HttpRequest):
        msg_status = messages.SUCCESS
        msg = format_html(f"Успех!<br/>{msg_text}")
        self.message_user(request, msg, msg_status)

    def merge_selected_patients(self, request: HttpRequest, queryset):
        """
        :type request: django.http.request.HttpRequest
        :type queryset: model_utils.managers.SoftDeletableQuerySet
        :rtype: None
        """

        if queryset.count() != 2:
            msg = _(f'Можно склеить только 2х пациентов')
            self.merge_patients_message_error(msg_text=msg, request=request)
            return

        patient_1: Patient = queryset[0]
        patient_2: Patient = queryset[1]
        error_extra = {"patient_ids": [patient_2.id, patient_1.id]}

        write_to_support_msg = (
            f'<a href="mailto:support@iclinincapp.ru">Обратитесь в поддержку</a> - '
            f'мы поможем корректно объединить пациентов :)'
        )

        # region validation
        if patient_1.is_removed or patient_2.is_removed:
            msg = format_html(
                f'<strong>Один из пациентов помечен как удаленный. '
                f'Нельзя объединять удаленных пациентов</strong>{write_to_support_msg}'
            )
            logging.warning(
                f"Patient merge attempt: {msg=}", extra=error_extra,
            )
            self.merge_patients_message_error(msg_text=msg, request=request)
            return

        if patient_2.user and patient_1.user:
            msg = format_html(
                f'<strong>У обоих пациентов указаны пользователи.</strong><br/>'
                f'{write_to_support_msg}'
            )
            logging.warning(
                f"Patient merge attempt: {msg=}", extra=error_extra,
            )
            self.merge_patients_message_error(msg_text=msg, request=request)
            return

        if not patient_1.user and not patient_2.user:
            msg = format_html(
                f'<strong>Нужно чтоб у одного из пациентов был указан пользователь.</strong><br/>'
                f'{write_to_support_msg}'
            )
            logging.warning(
                f"Patient merge attempt: {msg=}", extra=error_extra,
            )
            self.merge_patients_message_error(msg_text=msg, request=request)
            return

        to_patient = (patient_1.user and patient_1) or (patient_2.user and patient_2)
        from_patient = (not patient_1.user and patient_1) or (not patient_2.user and patient_2)
        if to_patient.id == from_patient.id:
            msg = format_html(
                f'<strong>'
                f'Внутренняя ошибка. Совпали ID пациентов.</strong>'
                f'<br/>{write_to_support_msg}'
            )
            logging.error(msg, extra=error_extra)
            self.merge_patients_message_error(msg_text=msg, request=request)
            return

        profile_1 = patient_1.profile
        profile_2 = patient_2.profile
        if (
            profile_1.last_name != profile_2.last_name
            or profile_1.first_name != profile_2.first_name
        ):
            msg = format_html(f'<strong>Фамилии и имена пациентов должны совпадать.</strong>')
            logging.warning(f"Patient merge attempt: {msg=}", extra=error_extra)
            self.merge_patients_message_error(msg_text=msg, request=request)
            return

        if to_patient.integration_data:
            msg = format_html(
                f'<strong>'
                f'У пациента {get_patient_href(to_patient)} уже указаны данные об интеграции.'
                f'</strong> <br/>{write_to_support_msg}'
            )
            logging.error(
                f"Patient merge attempt: {msg=}", extra=error_extra,
            )
            self.merge_patients_message_error(msg_text=msg, request=request)
            return
        # endregion
        updated_patient = PatientWorkflow.merge_patients(
            patient_from=from_patient,
            patient_to=to_patient,
            move_profile_groups=True,
            delete_patient_from=True,
        )
        msg = format_html(
            f'Перенесли данные из {get_patient_href(from_patient)} в {get_patient_href(to_patient)}. <br/>'
        )
        self.merge_patients_message_success(msg_text=msg, request=request)

    merge_selected_patients.short_description = _("Объединить пациентов. Не больше 2х за один раз.")


class PatientCRUDHistoryMixin(CRUDHistoryMixin, admin.ModelAdmin):
    def crud_history_action(self, request: HttpRequest, obj: Patient):
        related_obj_ids = get_patient_related_object_ids(patient=obj)
        base_history_url = reverse(f"admin:easyaudit_crudevent_changelist",)
        related_obj_ids__str = ",".join(map(str, related_obj_ids))

        content_type_ids = ContentType.objects.filter(
            app_label__in=("clinics", "moderation", "profiles", "reviews", "auth",),
            model__in=(
                "profile",
                "user",
                "patient",
                "review",
                "relation",
                "profilegroup",
                "contact",
            ),
        ).values_list("id", flat=True)
        content_type_ids = ",".join(map(str, content_type_ids))
        print(f"{content_type_ids=}")

        content_type_filter_str = (
            f"&content_type__id__in={content_type_ids}" if content_type_ids else ""
        )

        history_url = (
            f"{base_history_url}?object_id__in={related_obj_ids__str}{content_type_filter_str}"
        )
        print(f"{history_url=}")

        return redirect(history_url)


class PatientAppointmentListMixin(BaseProcessActionsAdminMixin, admin.ModelAdmin):
    APPOINTMENT_LIST = "appointment_list"

    def get_urls(self):
        urls = super(PatientAppointmentListMixin, self).get_urls()
        info = self._get_path_info()
        moderation_urls = [
            path(
                f'<path:object_id>/{self.APPOINTMENT_LIST}/',
                self.admin_site.admin_view(self.appointment_list_view),
                name=f'%s_%s_{self.APPOINTMENT_LIST}' % info,
            ),
        ]
        return moderation_urls + urls

    def get_action_methods(self):
        return {
            self.APPOINTMENT_LIST: self.appointment_list_action,
        }

    def appointment_list_view(self, request: HttpRequest, object_id: int):
        return self.process_action(request, object_id, self.APPOINTMENT_LIST)

    def appointment_list_action(self, request: HttpRequest, obj: Patient):
        patient_ids = [obj.id]
        admin_appointment_list_url = reverse(f"admin:appointments_appointment_changelist",)
        patient_ids__str = ",".join(map(str, patient_ids))

        appointment_list_url = f"{admin_appointment_list_url}?patient_id__in={patient_ids__str}"
        print(f"{appointment_list_url=}")

        return redirect(appointment_list_url)

    appointment_list_action.short_description = _('Appointment list')

    def get_appointment_list_url(self, obj: Patient):
        info = self._get_path_info()
        return reverse(f'admin:%s_%s_{self.APPOINTMENT_LIST}' % info, args=[obj.pk])
