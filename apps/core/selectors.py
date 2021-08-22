from abc import ABC
from typing import Union, Optional

from model_utils.models import SoftDeletableModel

from apps.core.models import DisplayableModel


class BaseSelector:
    model = None

    @classmethod
    def all(cls):
        """
        :rtype: django.db.models.query.QuerySet
        """
        return cls.model.objects.all()

    @classmethod
    def filter_by_params(cls, queryset, **kwargs):
        raise NotImplementedError

    @classmethod
    def get_by_id(cls, obj_id: int) -> model:
        manager = cls.model.objects
        if issubclass(cls.model, SoftDeletableModel):
            manager = cls.model.all_objects
        return manager.get(id=obj_id)

    @classmethod
    def get_or_none(cls, obj_id: int) -> Optional[model]:
        try:
            return cls.get_by_id(obj_id)
        except cls.model.DoesNotExist:
            return None


class SoftDeletedSelector(BaseSelector, ABC):
    @classmethod
    def all(cls):
        """
        :rtype: model_utils.managers.SoftDeletableQuerySet
        """
        return cls.model.objects.all()

    @classmethod
    def all_with_deleted(cls):
        """
        :rtype: model_utils.managers.SoftDeletableQuerySet
        """
        return cls.model.all_objects.all()


class DisplayedSelector(BaseSelector, ABC):
    model = DisplayableModel

    @classmethod
    def all(cls):
        """
        :rtype: apps.core.models.DisplayableQuerySet
        """
        return cls.model.objects.all()

    @classmethod
    def visible_to_patient(cls):
        """
        :rtype: apps.core.models.DisplayableQuerySet
        """
        return cls.all().displayed()
