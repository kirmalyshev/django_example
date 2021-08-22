from django.apps import AppConfig


class ClinicsConfig(AppConfig):
    name = 'apps.clinics'
    verbose_name = 'Данные клиники'

    def ready(self):
        pass
