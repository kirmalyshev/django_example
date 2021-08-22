# encoding=utf-8

from django.db.models.signals import ModelSignal

post_approved = ModelSignal(providing_args=["instance"], use_caching=True)
post_rejected = ModelSignal(providing_args=["instance"], use_caching=True)
post_send_to_moderation = ModelSignal(providing_args=["instance"], use_caching=True)
