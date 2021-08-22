from django.apps import AppConfig


class MobileNotificationsConfig(AppConfig):
    name = 'apps.mobile_notifications'
    verbose_name = 'Мобильные уведомления'
    label = 'mobile_notifications'

    def ready(self):
        pass
