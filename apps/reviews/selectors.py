from typing import Type, Union

from apps.clinics.models import Doctor
from apps.core.selectors import DisplayedSelector
from apps.reviews.models import Review


class ReviewSelector(DisplayedSelector):
    model = Review

    @classmethod
    def all(cls):
        """
        :rtype: apps.reviews.managers.ReviewQuerySet
        """
        return cls.model.objects.all()

    @classmethod
    def created_by_patient(cls, patient_id: Union[int, Type[int]]):
        """
        :rtype: apps.reviews.managers.ReviewQuerySet
        """
        return cls.all().created_by_patient(patient_id)

    @classmethod
    def filter_by_appointment_id(cls, appointment_id: int, **kwargs):
        """
        :rtype: apps.reviews.managers.ReviewQuerySet
        """
        qs = kwargs.get('queryset')
        if not qs:
            qs = cls.all()

        return qs.for_appointment(appointment_id)

    @classmethod
    def filter_by_doctor(cls, doctor: Doctor, **kwargs):
        """
        :rtype: apps.reviews.managers.ReviewQuerySet
        """
        qs = kwargs.get('queryset')
        if not qs:
            qs = cls.all()

        return qs.for_doctor(doctor)

    @classmethod
    def filter_by_params(cls, queryset, **kwargs):
        """
        :rtype: apps.reviews.managers.ReviewQuerySet
        """
        doctor_id = kwargs.get('doctor_id')

        qs = queryset.select_related('doctor',)
        if doctor_id and isinstance(doctor_id, int):
            # doctor_services = ServiceSelector.all().filter(id__in=service_ids)
            # with_ancestors = Service.tree_manager.get_queryset_ancestors(
            #     doctor_services, include_self=True).values_list('id', flat=True)
            # qs = qs.filter(services__id__in=with_ancestors)
            qs = qs.filter(doctor_id=doctor_id)
        return qs
