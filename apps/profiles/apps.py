# encoding=utf-8
import os

from django.apps import AppConfig


class ProfilesConfig(AppConfig):
    name = 'apps.profiles'
    verbose_name = 'Профили'
    label = 'profiles'
    app_name = 'profiles'

    def ready(self):
        from .models import User
