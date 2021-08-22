import re
from typing import Optional

from csvexport.actions import csvexport
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.http import HttpRequest
from django.shortcuts import render, redirect
from django.urls import path
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from apps.appointments.models import Appointment
from apps.clinics.admin_forms import ImportServicePricesForm
from apps.clinics.admin_tools import (
    HasProfilePhotoFilter,
    MergePatientsAdminMixin,
    PatientHasUserFilter,
    PatientCRUDHistoryMixin,
    PatientAppointmentListMixin,
    DoctorHasEducationFilter,
    DoctorHasYoutubeVideoFilter,
)
from apps.clinics.selectors import PatientSelector, DoctorSelector
from apps.clinics.tools import create_random_month_slots_for_doctor
from apps.core.admin import (
    DisplayableAdmin,
    DisplayableMPTTAdmin,
    DisableDeleteMixin,
    BaseProcessActionsAdminMixin,
)
from apps.feature_toggles.ops_features import django_admin__can_generate_doctor_timeslots
from apps.profiles.admin_utils import get_profile_links_as_common_str
from .constants import IMPORT_PRICES
from .models import (
    Service,
    Doctor,
    Patient,
    ClinicImage,
    Subsidiary,
    SubsidiaryImage,
    SubsidiaryContact,
    SubsidiaryWorkday,
    Promotion,
    ServicePrice,
    DoctorToService,
    DoctorToSubsidiary,
)
from ..core.constants import MODIFIED


@admin.register(ClinicImage)
class ClinicImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'image', 'priority')
    readonly_fields = (
        'created',
        'modified',
    )


class SubsidiaryImageInline(admin.TabularInline):
    model = SubsidiaryImage
    extra = 3


class SubsidiaryContactInline(admin.TabularInline):
    model = SubsidiaryContact
    extra = 2
    readonly_fields = (
        'created',
        'modified',
    )


class SubsidiaryWorkdayInline(admin.TabularInline):
    model = SubsidiaryWorkday
    extra = 1
    readonly_fields = (
        'created',
        'modified',
    )


@admin.register(SubsidiaryImage)
class SubsidiaryImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'subsidiary', 'is_primary')
    list_filter = ('subsidiary', 'is_primary')


@admin.register(Subsidiary)
class SubsidiaryAdmin(DisplayableAdmin, admin.ModelAdmin, DisableDeleteMixin):
    list_display = (
        'id',
        'title',
        'short_address',
        'integration_data',
        'is_removed',
        'is_displayed',
    )
    list_display_links = (
        'id',
        'title',
    )
    list_filter = (
        'is_displayed',
        'is_removed',
    )
    search_fields = ('title', 'address', 'short_address', 'integration_data')
    readonly_fields = (
        # 'latitude', 'longitude',  # TODO uncomment after maps available
        'created',
        'modified',
        'integration_data',
    )
    inlines = (SubsidiaryImageInline, SubsidiaryContactInline, SubsidiaryWorkdayInline)

    fieldsets = (
        (None, {'fields': ('title',)}),
        (
            _('Информация'),
            {'fields': ('description', 'address', 'short_address', 'latitude', 'longitude')},
        ),
        (_('Важные даты'), {'fields': ('created', 'modified')}),
        (_('Инфа из клиники'), {'fields': ('integration_data',)}),
        (_('Видимость'), {'fields': ('is_displayed', 'is_removed')}),
    )

    def get_queryset(self, request):
        queryset = self.model.all_objects.all()
        ordering = self.get_ordering(request)
        if ordering:
            queryset = queryset.order_by(*ordering)
        return queryset


class ServiceSubsidiaryInline(admin.TabularInline):
    model = Service.subsidiaries.through
    extra = 3
    raw_id_fields = ('subsidiary',)


class ServicePriceInline(admin.TabularInline):
    model = ServicePrice
    extra = 3
    fields = (
        'title',
        'price',
        'code',
        'priority',
        'is_displayed',
    )
    ordering = ("title",)


class ServiceDoctorInline(admin.TabularInline):
    model = DoctorToService
    extra = 3
    raw_id_fields = ('doctor',)
    verbose_name_plural = _('врачи, оказывающие эту услугу')


class ServiceImportPricesMixin(BaseProcessActionsAdminMixin, admin.ModelAdmin):
    def import_prices_view(self, request: HttpRequest, object_id: int):
        return self.process_action(request, object_id, IMPORT_PRICES)

    def get_action_methods(self):
        return {
            IMPORT_PRICES: self.import_prices_action,
        }

    def get_urls(self):
        urls = super(ServiceImportPricesMixin, self).get_urls()
        info = self._get_path_info()
        new_urls = [
            path(
                '<path:object_id>/import_prices/',
                self.admin_site.admin_view(self.import_prices_view),
                name='%s_%s_import_prices' % info,
            ),
        ]
        return new_urls + urls

    def import_prices__get(self, request: HttpRequest, obj: Service):
        form = ImportServicePricesForm(data=request.POST)
        payload = {"form": form}
        return render(request, "admin/clinics/import_prices.html", payload)

    price_re = re.compile(
        """(?P<index>[\d]+\.)? ?(?P<title>[\+а-яА-Я\w\\(\)\[\]\"\,-–—\/\d %№	]+) (?P<price>[\d\.]{2,})( |\n)?""",
        flags=re.U | re.I,
    )

    def import_prices__post(self, request: HttpRequest, obj: Service):
        data = request.POST
        prices_text = data.get("prices")
        prices = prices_text.split("\n")

        try:
            for i, item in enumerate(prices):
                match = self.price_re.match(item)
                if not match:
                    raise ValidationError(
                        f"Ошибка парсинга на {i + 1} строке. "
                        f"Не найдено соответствие регулярному выражению "
                        f"```{self.price_re.pattern}```"
                    )
                res: dict = match.groupdict()
                if not res:
                    raise ValidationError(f"Ошибка парсинга на {i + 1} строке")
                title: Optional[str] = res.get("title")
                title = title[0].capitalize() + title[1:]
                service = ServicePrice.objects.filter(service=obj, title=title).first()
                if not service:
                    service = ServicePrice.objects.create(service=obj, title=title)

                service.price = res.get("price")
                service.save()

            msg_status = messages.SUCCESS
            msg = _("Новые цены импортированы")
        except ValidationError as err:
            msg_status = messages.ERROR
            msg = err.message
        self.message_user(request, msg, msg_status)
        if msg_status == messages.SUCCESS:
            return redirect("..")
        else:
            return self.import_prices__get(request, obj)

    def import_prices_action(self, request: HttpRequest, obj: Service):

        if request.method == "POST":
            return self.import_prices__post(request, obj)
        return self.import_prices__get(request, obj)


@admin.register(Service)
class ServiceAdmin(DisplayableMPTTAdmin, ServiceImportPricesMixin):
    list_display = (
        'tree_actions',
        'indented_title',
        'subsidiary_titles',
        'is_displayed',
        'is_visible_for_appointments',
        'priority',
        'level',
        'tree_id',
        # 'lft',
        # 'rght',
    )

    list_display_links = ('indented_title',)
    raw_id_fields = ('subsidiaries',)
    list_filter = (
        'subsidiaries',
        'is_displayed',
        'is_visible_for_appointments',
    )
    ordering = ("tree_id", "level", "title")
    search_fields = ('title', 'description', 'slug')
    readonly_fields = ('created', 'modified', 'level', 'tree_id', 'lft', 'rght')
    fieldsets = (
        (None, {'fields': ('title', 'description', 'parent',)},),
        (_('Видимость'), {'fields': ('is_displayed', 'is_visible_for_appointments', 'priority',)},),
        (_('Системные'), {'fields': ('created', 'modified', 'level', 'tree_id', 'lft', 'rght')}),
    )
    inlines = (
        ServicePriceInline,
        ServiceSubsidiaryInline,
        ServiceDoctorInline,
    )

    def subsidiary_titles(self, obj: Service):
        return tuple(obj.subsidiaries.values_list("title", flat=True))


class DoctorServiceInline(admin.TabularInline):
    model = DoctorToService
    extra = 3
    raw_id_fields = ('service',)


class DoctorSubsidiaryInline(admin.TabularInline):
    model = DoctorToSubsidiary
    extra = 3
    raw_id_fields = ('subsidiary',)


@admin.register(Doctor)
class DoctorAdmin(DisplayableAdmin, admin.ModelAdmin):
    date_hierarchy = MODIFIED
    list_display = (
        'id',
        'public_full_name',
        'profile',
        'speciality_text',
        'status',
        'is_displayed',
        'is_timeslots_available_for_patient',
        'is_fake',
        'is_removed',
        'is_totally_hidden',
        'created',
        'modified',
    )
    list_display_links = (
        'id',
        'public_full_name',
        'profile',
    )
    list_filter = (
        'is_displayed',
        'status',
        HasProfilePhotoFilter,
        DoctorHasEducationFilter,
        DoctorHasYoutubeVideoFilter,
        'subsidiaries',
        'is_fake',
        'is_removed',
        'is_totally_hidden',
        'speciality_text',
        'is_timeslots_available_for_patient',
        'services',
        'created',
        'modified',
    )
    search_fields = (
        'id',
        'public_full_name',
        'public_short_name',
        'speciality_text',
        'profile__full_name',
        'integration_data',
    )
    ordering = (
        '-created',
        '-modified',
        'public_full_name',
        'profile__full_name',
    )
    fieldsets = (
        (None, {'fields': ('profile', 'full_name', 'public_full_name', 'public_short_name')}),
        (
            _('Информация'),
            {
                'fields': (
                    'description',
                    'experience',
                    'speciality_text',
                    'education',
                    'status',
                    'is_displayed',
                    'is_fake',
                    # 'is_removed',
                    'is_totally_hidden',
                    'is_timeslots_available_for_patient',
                    "youtube_video_link",
                    "youtube_video_id",
                )
            },
        ),
        (_('Инфа из клиники'), {'fields': ('integration_data',)}),
        (_('Важные даты'), {'fields': ('status_changed', 'created', 'modified')},),
    )
    readonly_fields = (
        'status_changed',
        'created',
        'modified',
        'integration_data',
        'full_name',
        "youtube_video_id",
    )
    raw_id_fields = ('profile', 'subsidiaries', 'services')
    inlines = (DoctorServiceInline, DoctorSubsidiaryInline)
    exclude = ('services', 'subsidiaries')

    actions = (
        "make_displayed",
        "make_hidden",
        "generate_timeslots_action",
        csvexport,
    )

    def get_actions(self, request):
        actions = super(DoctorAdmin, self).get_actions(request)
        if not django_admin__can_generate_doctor_timeslots.is_enabled:
            actions.pop("generate_timeslots_action", None)
        return actions

    def generate_timeslots_action(self, request, queryset):
        for doctor in queryset.iterator():
            create_random_month_slots_for_doctor(doctor)

    generate_timeslots_action.short_description = _(
        'Сгенерировать случайные таймслоты на месяц вперед'
    )

    def get_queryset(self, request):
        queryset = DoctorSelector.all_with_deleted().prefetch_related('services', 'subsidiaries')
        ordering = self.get_ordering(request)
        if ordering:
            queryset = queryset.order_by(*ordering)
        return queryset


class AppointmentInline(admin.TabularInline):
    model = Appointment
    fk_name = "patient"
    show_change_link = True
    raw_id_fields = (
        'service',
        'doctor',
        'subsidiary',
    )
    ordering = (
        '-start',
        'modified',
    )
    readonly_fields = fields = (
        'start',
        'end',
        'doctor',
        'service',
        'subsidiary',
        'reason_text',
        'price',
        'created_by_type',
        'status',
        'integration_data',
        'created',
    )
    extra = 1

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Patient)
class PatientAdmin(
    PatientCRUDHistoryMixin, PatientAppointmentListMixin, MergePatientsAdminMixin,
):
    actions = ("merge_selected_patients",)
    list_display = (
        'id',
        'full_info',
        'get_profile_links',
        'integration_data',
        'is_confirmed',
        'is_removed',
        'created',
    )
    date_hierarchy = "created"
    list_display_links = (
        'id',
        'full_info',
    )
    search_fields = (
        'id',
        'profile__full_name',
        'profile__users__username',
        'profile__users__contacts__value',
        "integration_data",
    )
    list_filter = (
        PatientHasUserFilter,
        'is_confirmed',
        'is_removed',
        'created',
        'modified',
    )
    ordering = ('-created',)
    inlines = (AppointmentInline,)
    raw_id_fields = ('profile',)
    readonly_fields = (
        'get_profile_links',
        'created',
        'modified',
        'integration_data',
    )
    fieldsets = (
        (None, {'fields': ('profile', 'get_profile_links',)},),
        (_('Информация'), {'fields': ('is_confirmed', 'is_removed',)},),
        (_('Интеграция'), {'fields': ('integration_data',)}),
        (_('Важные даты'), {'fields': ('created', 'modified')}),
    )

    def get_profile_links(self, obj: Patient) -> str:
        if obj.profile_id:
            profile_links = get_profile_links_as_common_str(
                obj.profile, start_string=None, with_contacts=True
            )
        else:
            profile_links = ""

        crud_history_url = self.get_crud_history_url(obj=obj)
        crud_history_a = f"<a href={crud_history_url}>> {self.crud_history_translated_title}</a>"

        appointment_list_url = self.get_appointment_list_url(obj=obj)
        appointment_list_a = (
            f"<a href={appointment_list_url}>> {self.appointment_list_action.short_description}</a>"
        )

        all_links = f"{profile_links}</br>{crud_history_a}</br>{appointment_list_a}"

        return mark_safe(all_links)

    get_profile_links.short_description = _('ссылки')

    def get_queryset(self, request):
        queryset = (
            PatientSelector.all_with_deleted()
            .select_related('profile')
            .prefetch_related('profile__users', 'profile__users__contacts')
        )
        ordering = self.get_ordering(request)
        if ordering:
            queryset = queryset.order_by(*ordering)
        return queryset


@admin.register(Promotion)
class PromotionAdmin(DisplayableAdmin, admin.ModelAdmin):
    search_fields = ('id', 'title', 'content')
    list_display = ('id', 'title', 'published_from', 'published_until', 'is_displayed')
    list_filter = ('published_from', 'published_until', 'is_displayed')
    readonly_fields = (
        'created',
        'modified',
        'publication_range_text',
    )

    fieldsets = (
        (
            None,
            {'fields': ('title', 'primary_image', 'content', 'subsidiaries', 'ordering_number')},
        ),
        (
            _('Публикация'),
            {
                'fields': (
                    'is_displayed',
                    'published_from',
                    'published_until',
                    'publication_range_text',
                )
            },
        ),
        (_('Важные даты'), {'fields': ('created', 'modified')}),
    )
