# encoding=utf-8

from __future__ import print_function
from __future__ import unicode_literals

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.http import Http404
from django.shortcuts import get_object_or_404


class ModeratedManager(models.Manager):
    queryset_class = models.QuerySet

    def get_queryset(self):
        return (
            self.queryset_class(self.model, using=self._db)
            .filter(is_displayed=True)
            .prefetch_related('moderation_requests')
        )


class DefaultModeratedManager(models.Manager):
    queryset_class = models.QuerySet

    def get_queryset(self):
        return self.queryset_class(self.model, using=self._db).prefetch_related(
            'moderation_requests'
        )

    def create(self, **kwargs):
        """
        Creates a new object with the given kwargs, saving it to the database
        and returning the created object.
        """
        obj = self.model(**kwargs)
        self._for_write = True
        obj.save(force_insert=True, using=self.db, skip_moderation=True)
        return obj

    def get_for_owner_or_404(self, owner, **kwargs):
        moderate_model = register.get_moderator_class(self.model)
        assert moderate_model.owner_field, 'Moderator {} lacks owner_field setting'.format(
            moderate_model.__name__
        )

        instance = get_object_or_404(self, **kwargs)
        if not instance.is_approved and getattr(instance, moderate_model.owner_field) != owner:
            raise Http404
        return instance


class FieldHistoryManager(models.Manager):
    def record_history(self, obj, changes, changed_by=None):
        history_objects = []
        for field, values in changes.items():
            old_value = '{}'.format(values[0])
            new_value = '{}'.format(values[1])
            history_objects.append(
                self.model(
                    content_object=obj,
                    name=field,
                    old_value=old_value,
                    new_value=new_value,
                    changed_by=changed_by,
                )
            )
        return history_objects


class RequestManager(models.Manager):
    def get_for_object(self, obj):
        content_type = ContentType.objects.get_for_model(obj)
        return self.filter(content_type=content_type, object_id=obj.id)

    def get_for_model(self, model):
        content_type = ContentType.objects.get_for_model(model)
        return self.filter(content_type=content_type)

    def get_first_approved(self, obj):
        from .models import ModerationRequest

        try:
            return (
                self.get_for_object(obj)
                .filter(status=ModerationRequest.STATUS_APPROVED)
                .earliest('moderated_timestamp')
            )
        except Request.DoesNotExist:
            return
