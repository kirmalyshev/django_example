from django.db.models.signals import Signal

push_notification_event_received = Signal(
    providing_args=["push_uuid", "event_type", "event_labels"]
)
push_notification_sent = Signal(providing_args=["push_uuid", "event_labels"])
