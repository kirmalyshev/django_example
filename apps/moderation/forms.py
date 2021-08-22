# -*- coding: utf-8 -*-

from django import forms
from django.contrib.admin import widgets

from apps.moderation import models


class RequestAdminForm(forms.ModelForm):
    created = forms.DateTimeField(widget=widgets.AdminSplitDateTime)

    class Meta:
        model = models.ModerationRequest
        fields = '__all__'
