from csvexport.actions import csvexport

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.core.exceptions import ObjectDoesNotExist
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _
from push_notifications.models import GCMDevice

from apps.core.admin import get_change_href
from apps.profiles.admin_utils import get_user_link, UserHasPhoneFilter
from apps.profiles.constants import BIRTH_DATE
from apps.profiles.models import (
    User,
    Profile,
    Contact,
    ContactVerification,
    UserToProfile,
    ProfileGroup,
    Relation,
    ProfileToGroup,
)
from apps.core.constants import CREATED, MODIFIED


class ContactInlineAdmin(admin.TabularInline):
    model = Contact


class GCMDeviceInline(admin.TabularInline):
    model = GCMDevice
    can_delete = False
    extra = 0
    readonly_fields = (
        'name',
        'active',
        'application_id',
        'registration_id',
        'device_id',
        'cloud_message_type',
        'date_created',
    )

    def has_add_permission(self, request, obj=None):
        return False


class UserToProfileInline(admin.TabularInline):
    model = UserToProfile
    can_delete = False
    extra = 0
    raw_id_fields = (
        'profile',
        'user',
    )
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    class Media:
        js = ("profiles/user_admin.js",)

    list_display = ('username', "links_fn", 'is_staff', 'created', "modified")
    ordering = (
        '-created',
        '-modified',
    )
    list_filter = (
        UserHasPhoneFilter,
        'is_active',
        'is_staff',
        'created',
        'modified',
    )
    search_fields = ('username', 'profile__full_name', 'contacts__value')
    readonly_fields = (
        'email',
        'last_login',
        'last_visited',
        'date_joined',
        'links_fn',
        'created',
        'modified',
    )
    raw_id_fields = ('groups',)
    inlines = (UserToProfileInline, ContactInlineAdmin, GCMDeviceInline)

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Информация'), {'fields': ('links_fn',)}),
        (
            _('Permissions'),
            {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')},
        ),
        (
            _('Системная информация'),
            {'fields': ('last_login', 'date_joined', 'last_visited', 'created', 'modified')},
        ),
    )

    def links_fn(self, obj: User):
        profile_link = ""
        profile: Profile = obj.profile
        if profile:
            profile_link = get_change_href(profile, label=f"Профиль: {profile.short_full_name}")
            profile_link = f"> {profile_link}"

        patient_link = ""
        try:
            patient_link = obj.patient and f"> {get_change_href(obj.patient, label=f'пациент')}"
        except ObjectDoesNotExist as err:
            patient_link = ""

        if not any((profile_link, patient_link)):
            return ""

        links = format_html(f"{profile_link or ''}<br/>{patient_link or ''}")
        return links

    links_fn.short_description = _('ссылки')

    def get_queryset(self, request):
        qs = super(UserAdmin, self).get_queryset(request)
        qs = qs.prefetch_related('profile_set', 'contacts', 'gcmdevice_set', 'profile_set__patient')
        return qs


class ProfileToGroupInline(admin.TabularInline):
    model = ProfileToGroup
    show_change_link = True
    raw_id_fields = ('profile',)
    verbose_name_plural = _('профили в группе')
    fields = ('profile',)


@admin.register(ProfileGroup)
class ProfileGroupAdmin(admin.ModelAdmin):
    search_fields = ('title', 'type')
    inlines = (ProfileToGroupInline,)
    readonly_fields = (
        'created',
        'modified',
        'integration_data',
    )
    list_display = ('id', 'title', 'type', 'integration_data', 'profile_ids')
    fieldsets = (
        (_('Общее'), {'fields': ('title', 'type',)},),
        (_('Интеграция'), {'fields': ('integration_data',)}),
        (_('Системная информация'), {'fields': ('created', 'modified')}),
    )

    def profile_ids(self, obj: ProfileGroup):
        profile_ids = list(obj.profiles.all().distinct().values_list('id', flat=True))
        return f'{profile_ids}'


@admin.register(Relation)
class RelationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "master",
        "slave",
        "type",
        "can_update_slave_appointments",
        CREATED,
    )
    readonly_fields = (
        CREATED,
        MODIFIED,
    )
    list_filter = ('type', 'can_update_slave_appointments')
    raw_id_fields = (
        'master',
        'slave',
    )
    fieldsets = (
        (_('Общее'), {'fields': ('master', 'slave', 'type', 'can_update_slave_appointments',)},),
        (_('Системная информация'), {'fields': (CREATED, MODIFIED)}),
    )


class ProfileGroupInline(admin.TabularInline):
    verbose_name = _("Группа профилей")
    verbose_name_plural = _("Группы профилей")
    model = ProfileToGroup
    show_change_link = True
    raw_id_fields = ('group',)


class MasterRelationInline(admin.TabularInline):
    verbose_name = _("Зависимый профиль")
    verbose_name_plural = _("Зависимые профили")
    model = Relation
    fk_name = 'master'
    raw_id_fields = ('slave',)
    extra = 1
    readonly_fields = ('master',)


class SlaveRelationInline(admin.TabularInline):
    verbose_name = _("Родительский профиль для текущего")
    verbose_name_plural = _("Родительские профили")
    model = Relation
    fk_name = 'slave'
    raw_id_fields = ('master',)
    extra = 1
    readonly_fields = ('slave',)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    date_hierarchy = "created"
    list_display = ('id', 'full_name', BIRTH_DATE, 'links_fn', 'type', 'is_active', 'created')
    list_display_links = ('id', 'full_name')
    search_fields = ('id', 'users__contacts__value', 'users__name', 'full_name')
    list_filter = (
        'created',
        'modified',
        'is_active',
        'type',
        BIRTH_DATE,
    )
    readonly_fields = ('full_name', 'links_fn', 'created', 'modified')
    inlines = (
        ProfileGroupInline,
        MasterRelationInline,
        SlaveRelationInline,
        UserToProfileInline,
    )
    fieldsets = (
        (None, {'fields': ('full_name', 'last_name', 'first_name', 'patronymic')}),
        (
            _('Общая информация'),
            {'fields': ('birth_date', 'gender', 'picture_draft', 'region_as_text', "links_fn",)},
        ),
        (_('Системная информация'), {'fields': ('type', 'created', 'modified')}),
    )

    def links_fn(self, obj: Profile):
        user_link = get_user_link(obj.user,)
        if user_link:
            user_link = f"> {user_link}"
        patient_link = ""
        try:
            patient_link = obj.patient and f"> {get_change_href(obj.patient, label=f'пациент')}"
        except ObjectDoesNotExist as err:
            patient_link = ""

        if not any((user_link, patient_link)):
            return ""

        links = format_html(f"{user_link or ''}<br/>{patient_link or ''}")
        return links

    links_fn.short_description = _('ссылки')

    def get_queryset(self, request):
        qs = super(ProfileAdmin, self).get_queryset(request)
        qs = qs.select_related('patient', "doctor").prefetch_related("users",)
        return qs


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'type',
        'value',
        'is_confirmed',
        'is_rejected',
        'is_deleted',
        'created',
        'modified',
    )
    list_filter = ('is_confirmed', 'is_rejected', 'type', 'is_deleted')
    raw_id_fields = ['user']
    search_fields = ['value']
    readonly_fields = (
        'created',
        'modified',
    )
    actions = (csvexport,)

    def get_queryset(self, request):
        return self.model.default_manager.all().select_related("user",)


@admin.register(ContactVerification)
class ContactVerificationAdmin(admin.ModelAdmin):
    date_hierarchy = CREATED
    list_display = (
        'contact_value_fn',
        'contact_type_fn',
        'is_primary_fn',
        'code',
        'user_fn',
        CREATED,
        MODIFIED,
    )
    search_fields = ('contact__value', 'contact__user__profile__full_name', 'code')
    raw_id_fields = ('contact',)
    readonly_fields = (CREATED, MODIFIED)

    def is_primary_fn(self, obj):
        return obj.contact.is_primary

    is_primary_fn.short_description = _('основной?')
    is_primary_fn.admin_order_field = 'contact__is_primary'
    is_primary_fn.boolean = True

    def contact_value_fn(self, obj):
        return obj.contact.value

    contact_value_fn.short_description = _('контакт')
    contact_value_fn.admin_order_field = 'contact__value'

    def contact_type_fn(self, obj):
        return obj.contact.type

    contact_type_fn.short_description = _('тип контакта')
    contact_type_fn.admin_order_field = 'contact__type'

    def user_fn(self, obj):
        user = obj.contact.user
        admin_url = user.get_admin_url()
        return format_html(f'<a href="{admin_url}">{user}</a>')

    user_fn.short_description = _('пользователь')
    user_fn.admin_order_field = 'contact__user'
    user_fn.allow_tags = True
