from datetime import datetime
from django.db import models
from django.db.models import Q, Manager, QuerySet
from django.utils import timezone
from mptt.querysets import TreeQuerySet

from apps.core.models import (
    DisplayableQuerySet,
    DeletableDisplayableQuerySet,
    DisplayableMPTTManager,
    DeletableDisplayableManager,
    DisplayableManager,
)


class SubsidiaryImageQuerySet(models.QuerySet):
    def only_primary(self):
        return self.filter(is_primary=True)

    def not_primary(self):
        return self.filter(is_primary=False)


class SubsidiaryImageManager(models.Manager):
    def get_queryset(self) -> SubsidiaryImageQuerySet:
        return SubsidiaryImageQuerySet(self.model, using=self._db)

    def unset_primary(self, exclude_pk=None):
        """
        Remove `is_primary` flag from all primary images of supplied subsidiary
        (except passed in `exclude_pk`)
        """
        existing_primary = self.all().only_primary()
        if exclude_pk:
            existing_primary = existing_primary.exclude(pk=exclude_pk)

        existing_primary.update(is_primary=False)


class PromotionQuerySet(DisplayableQuerySet):
    def displayed(self):
        now = timezone.now()
        return self.filter(is_displayed=True).filter(
            Q(published_from__lte=now) | Q(published_until__gt=now)
        )


class ServiceQuerySet(DeletableDisplayableQuerySet, TreeQuerySet):
    def visible_for_appointments(self):
        """
        :rtype: ServiceQuerySet
        """
        return self.filter(is_visible_for_appointments=True)

    def only_root(self):
        """
        :rtype: ServiceQuerySet
        """
        return self.filter(level=0)

    def for_parent_id(self, parent_id: int):
        """
        :rtype: ServiceQuerySet
        """
        return self.filter(parent_id=parent_id)

    def with_real_visible_doctors(self):
        """
        :rtype: ServiceQuerySet
        """
        from apps.clinics.models import DoctorToService

        service_ids = DoctorToService.objects.filter(
            doctor__isnull=False, doctor__is_fake=False, doctor__is_displayed=True
        ).values_list('service_id', flat=True)
        return self.filter(id__in=service_ids)


class ServiceManager(DisplayableMPTTManager):
    def get_queryset(self, *args, **kwargs) -> ServiceQuerySet:
        qs = ServiceQuerySet(self.model, using=self._db, **kwargs).order_by(
            self.tree_id_attr, self.left_attr
        )
        return qs


class ProfileInvolvedQuerySetMixin(QuerySet):
    def filter_by_full_name(self, full_name: str):
        full_name_q = Q(Q(profile__full_name=full_name) | Q(public_full_name=full_name))
        return self.filter(full_name_q)

    def filter_by_birth_date(self, birth_date: datetime):
        return self.filter(profile__birth_date=birth_date)


class DoctorQuerySet(ProfileInvolvedQuerySetMixin, DeletableDisplayableQuerySet):
    def without_hidden(self):
        return self.exclude(is_totally_hidden=True)


class DoctorManager(Manager.from_queryset(DoctorQuerySet), DeletableDisplayableManager):
    pass


class DoctorAllManager(Manager.from_queryset(DoctorQuerySet), DisplayableManager):
    pass
