from django.utils.translation import ugettext_lazy as _

from apps.core.constants import BaseStatus

GRADE = 'grade'

MAX_REVIEW_REQUEST_DAYS = 7


class ReviewStatus(BaseStatus):
    NEW = 0
    ON_MODERATION = 1
    PROCESSED = 2

    VALUES = {
        NEW: _('новый'),
        ON_MODERATION: _('на модерации'),
        PROCESSED: _('обработан'),
    }

    VALUE_KEYS = VALUES.keys()

    CHOICES = VALUES.items()
