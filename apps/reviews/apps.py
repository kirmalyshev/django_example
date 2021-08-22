from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class ReviewConfig(AppConfig):
    name = 'apps.reviews'
    verbose_name = _('Отзывы')
    label = 'reviews'

    def ready(self):
        pass
