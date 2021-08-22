from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class AppointmentsConfig(AppConfig):
    name = 'apps.support'
    verbose_name = _('Frequently Asked Questions')

    def ready(self):
        pass
