from django.db import models
from django.db.models import Manager, QuerySet
from django.utils.translation import ugettext_lazy as _

from model_utils.fields import AutoCreatedField, AutoLastModifiedField
from model_utils.managers import SoftDeletableManager, SoftDeletableQuerySet
from model_utils.models import TimeStampedModel, SoftDeletableModel
from mptt.managers import TreeManager
from mptt.models import MPTTModel


class ReloadableModel(models.Model):
    def reload(self):
        manager = self.__class__.objects
        if hasattr(self.__class__, '_default_manager'):
            manager = self.__class__._default_manager
        elif hasattr(self.__class__, 'default_manager'):
            manager = self.__class__.default_manager
        return manager.get(pk=self.pk)

    class Meta:
        abstract = True


class TimeStampIndexedModel(ReloadableModel, TimeStampedModel):
    """
    An abstract base class model that provides indexed self-updating
    ``created`` and ``modified`` fields.

    """

    created = AutoCreatedField(_('created'), db_index=True)
    modified = AutoLastModifiedField(_('modified'))

    class Meta:
        abstract = True


class ClinicSoftDeletableModel(SoftDeletableModel):
    is_removed = models.BooleanField(_('удален'), default=False)

    class Meta:
        abstract = True


# region Displayable


class DisplayableQuerySet(QuerySet):
    def displayed(self):
        return self.filter(is_displayed=True)

    def published(self):
        return self.displayed()

    def hidden(self):
        return self.filter(is_displayed=False)

    def mark_hidden(self) -> None:
        self.update(is_displayed=False)

    def mark_displayed(self) -> None:
        self.update(is_displayed=True)


class DisplayableManager(Manager.from_queryset(DisplayableQuerySet)):
    def displayed(self):
        return self.filter(is_displayed=True)

    def hidden(self):
        return self.filter(is_displayed=False)

    def mark_hidden(self) -> None:
        self.update(is_displayed=False)

    def mark_displayed(self) -> None:
        self.update(is_displayed=True)


class DisplayableModel(models.Model):
    is_displayed = models.BooleanField(_('отображается?'), default=True, db_index=True)

    objects = DisplayableManager()

    class Meta:
        abstract = True

    def mark_hidden(self, save=True):
        if not self.is_displayed:
            return
        self.is_displayed = False
        if save:
            self.save()

    def mark_displayed(self, save=True):
        if self.is_displayed:
            return
        self.is_displayed = True
        if save:
            self.save()


# endregion

# region SoftDeletable + Displayable
class DeletableDisplayableQuerySet(SoftDeletableQuerySet, DisplayableQuerySet):
    pass


class DeletableDisplayableManager(
    Manager.from_queryset(DeletableDisplayableQuerySet), SoftDeletableManager
):
    pass


class DeletableDisplayable(SoftDeletableModel, DisplayableModel):
    objects = DeletableDisplayableManager()
    all_objects = DisplayableManager()

    class Meta:
        abstract = True
        default_manager_name = 'all_objects'

    def save(self, **kwargs):
        if self.is_removed:
            self.mark_hidden(save=False)
        super(DeletableDisplayable, self).save(**kwargs)


# endregion


class DisplayableMPTTManager(DisplayableManager, TreeManager):
    def get_queryset(self, *args, **kwargs):
        """
        Ensures that this manager always returns nodes in tree order.
        """
        return (
            super(DisplayableMPTTManager, self)
            .get_queryset(*args, **kwargs)
            .order_by(self.tree_id_attr, self.left_attr)
        )


class DisplayableMPTTModel(MPTTModel, DisplayableModel):
    objects = DisplayableMPTTManager()

    class Meta:
        abstract = True
