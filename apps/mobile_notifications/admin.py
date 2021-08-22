# encoding=utf-8
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _
from push_notifications.admin import DeviceAdmin
from push_notifications.models import APNSDevice, GCMDevice, WebPushDevice, WNSDevice

from apps.mobile_notifications.models import PushLog
from apps.profiles.admin_utils import get_user_link, get_profile_link


class APNSDeviceAdmin(DeviceAdmin):
    raw_id_fields = ['user']
    search_fields = (
        "name",
        "device_id",
        "user__username",
        "user__name",
        "application_id",
    )


class GCMDeviceAdmin(DeviceAdmin):
    list_display = (
        "__str__",
        "device_id",
        "user",
        "active",
        "date_created",
        "registration_id",
        "application_id",
    )
    raw_id_fields = ['user']
    search_fields = ("name", "device_id", "user__username", "user__name", "application_id")
    list_filter = (
        "active",
        "application_id",
        "date_created",
    )


@admin.register(PushLog)
class PushLogAdmin(admin.ModelAdmin):
    date_hierarchy = "created"
    raw_id_fields = ('user',)
    list_display = ('id', 'created', 'event_name', 'user_links_fn', "appointment_id", 'data')
    list_display_links = (
        'id',
        'created',
    )
    list_filter = ('event_name', 'created')
    search_fields = (
        'data',
        'event_name',
        "appointment_id",
    )
    readonly_fields = (
        'created',
        'modified',
        "appointment_id",
        'data',
        'event_name',
    )

    def has_add_permission(self, request):
        return False

    def user_links_fn(self, obj: PushLog):
        user = obj.user
        if not user:
            return
        user_link = get_user_link(user)
        profile_link = get_profile_link(user.profile)
        return format_html(f"{user_link}</br>{profile_link}")

    user_links_fn.short_description = _('пользователь/профиль')


admin.site.unregister(APNSDevice)
admin.site.unregister(GCMDevice)
admin.site.unregister(WebPushDevice)
admin.site.unregister(WNSDevice)
admin.site.register(APNSDevice, APNSDeviceAdmin)
admin.site.register(GCMDevice, GCMDeviceAdmin)
