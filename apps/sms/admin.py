# encoding=utf-8

from __future__ import print_function, unicode_literals

from django.contrib import admin

from .models import PhoneCode, SMSCode


class SMSCodeAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone_number', 'value', 'is_used', 'created']
    search_fields = ['phone_number', 'user__contacts__value']
    raw_id_fields = ['user']
    readonly_fields = (
        'created',
        'modified',
    )
    list_filter = (
        'is_used',
        'created',
    )


class PhoneCodeAdmin(admin.ModelAdmin):
    list_display = ['code', 'is_wired', 'provider']
    list_filter = ['is_wired']
    search_fields = [
        'code',
        'provider',
    ]


admin.site.register(PhoneCode, PhoneCodeAdmin)
admin.site.register(SMSCode, SMSCodeAdmin)
