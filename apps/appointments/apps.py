from django.apps import AppConfig


class AppointmentsConfig(AppConfig):
    name = 'apps.appointments'
    verbose_name = ' Работа с записями на прием'

    def ready(self):
        pass

        from . import tasks  # dont delete

        # from . import signal_handlers
