# encoding=utf-8

from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'apps.core'
    verbose_name = name

    def ready(self):
        pass
