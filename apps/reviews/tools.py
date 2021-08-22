from datetime import timedelta

from apps.appointments.models import Appointment
from apps.core.utils import now_in_default_tz
from apps.feature_toggles.ops_features import is_reviews_enabled
from apps.reviews.constants import MAX_REVIEW_REQUEST_DAYS


def is_adding_review_allowed(appointment: Appointment) -> bool:
    if not is_reviews_enabled.is_enabled:
        return False

    if not appointment.is_finished:
        return False

    if appointment.has_reviews:
        return False

    if appointment.end:
        delta = now_in_default_tz() - appointment.end
        if delta.days > MAX_REVIEW_REQUEST_DAYS:
            return False

    return True
