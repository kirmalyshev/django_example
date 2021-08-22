from collections import Iterable
from typing import Optional

from django.db.models import QuerySet

from apps.clinics.constants import ONLY_ROOT, PARENT_ID, MobileAppSections
from apps.clinics.managers import ServiceQuerySet
from apps.clinics.models import Doctor, Patient, Subsidiary, Service
from apps.core.selectors import SoftDeletedSelector, DisplayedSelector
from apps.integration.constants import SubsidiaryIntegrationData, MIS_SUBSIDIARY_ID
from apps.profiles.models import Relation, Profile


class DoctorSelector(SoftDeletedSelector, DisplayedSelector):
    model = Doctor

    @classmethod
    def all(cls):
        """
        :rtype: apps.clinics.managers.DoctorQuerySet
        """
        return (
            cls.model.objects.all()
            .select_related('profile')
            .prefetch_related('services')
            .order_by('public_full_name',)
        )

    @classmethod
    def all_with_deleted(cls):
        """
        :rtype: apps.clinics.managers.DoctorQuerySet
        """
        return (
            cls.model.all_objects.all()
            .select_related('profile')
            .prefetch_related('services')
            .order_by('public_full_name')
        )

    @classmethod
    def visible_to_patient(cls):
        """
        :rtype: apps.clinics.managers.DoctorQuerySet
        """
        return cls.all().displayed().without_hidden()

    @classmethod
    def filter_by_params(cls, queryset, **kwargs):
        """
        :rtype: apps.clinics.managers.DoctorQuerySet
        """
        service_ids = kwargs.get('service_ids')
        subsidiary_ids = kwargs.get('subsidiary_ids')
        without_fakes = kwargs.get('without_fakes')

        qs = queryset.prefetch_related('services', 'subsidiaries')
        if service_ids and isinstance(service_ids, Iterable):
            # doctor_services = ServiceSelector.all().filter(id__in=service_ids)
            # with_ancestors = Service.tree_manager.get_queryset_ancestors(
            #     doctor_services, include_self=True).values_list('id', flat=True)
            # qs = qs.filter(services__id__in=with_ancestors)
            qs = qs.filter(services__id__in=service_ids)

        if subsidiary_ids and isinstance(subsidiary_ids, Iterable):
            qs = qs.filter(subsidiaries__id__in=subsidiary_ids)

        if without_fakes:
            qs = qs.filter(is_fake=False)

        return qs.distinct()


class SubsidiarySelector(SoftDeletedSelector, DisplayedSelector):
    model = Subsidiary

    @classmethod
    def all(cls):
        """
        :rtype: apps.core.models.DeletableDisplayableQuerySet
        """
        return cls.model.objects.all().prefetch_related('images')

    @classmethod
    def all_with_deleted(cls):
        """
        :rtype: django.db.models.query.QuerySet
        """
        return cls.model.all_objects.all().prefetch_related('images')

    @classmethod
    def visible_to_patient(cls):
        """
        :rtype: apps.core.models.DeletableDisplayableQuerySet
        """
        return cls.all().displayed()

    @classmethod
    def get_by_integration_id(cls, mis_subsidiary_id: int) -> Optional[Subsidiary]:
        contains: SubsidiaryIntegrationData = {MIS_SUBSIDIARY_ID: mis_subsidiary_id}
        qs = SubsidiarySelector.all().filter(integration_data__contains=contains)
        try:
            subsidiary: Subsidiary = qs.get()
            return subsidiary
        except Subsidiary.DoesNotExist as err:
            return None

    @classmethod
    def get_integration_id_for_subsidiary(cls, subsidiary: Subsidiary) -> Optional[int]:
        data: SubsidiaryIntegrationData = subsidiary.integration_data
        if not data:
            return
        return data[MIS_SUBSIDIARY_ID]


class ServiceSelector(SoftDeletedSelector, DisplayedSelector):
    model = Service

    @classmethod
    def all(cls):
        """
        :rtype: apps.clinics.managers.ServiceQuerySet
        """
        return (
            cls.model.objects.all().prefetch_related('subsidiaries').order_by('-priority', "title")
        )

    @classmethod
    def visible_to_patient(cls):
        """
        :rtype: apps.clinics.managers.ServiceQuerySet
        """
        return cls.all().displayed()

    @classmethod
    def filter_by_params(cls, queryset: ServiceQuerySet, **kwargs) -> QuerySet:
        subsidiary_ids = kwargs.get('subsidiary_ids')
        only_root = kwargs.get(ONLY_ROOT)
        parent_id = kwargs.get(PARENT_ID)
        mobile_app_section = kwargs.get('mobile_app_section', '')

        if only_root and parent_id:
            raise ValueError(f'one of params [{ONLY_ROOT}, {PARENT_ID}] must be in kwargs')

        if only_root:
            queryset = queryset.only_root()
        elif parent_id:
            queryset = queryset.for_parent_id(parent_id)

        if subsidiary_ids and isinstance(subsidiary_ids, Iterable):
            queryset = queryset.filter(subsidiaries__id__in=subsidiary_ids).distinct()

        if mobile_app_section == MobileAppSections.DOCTORS:
            queryset = queryset.visible_for_appointments().with_real_visible_doctors()
        elif mobile_app_section == MobileAppSections.SERVICES:
            pass
        elif mobile_app_section == MobileAppSections.CREATE_APPOINTMENT_BY_PATIENT:
            queryset = queryset.visible_for_appointments().with_real_visible_doctors()

        return queryset


class PatientSelector(SoftDeletedSelector, DisplayedSelector):
    model = Patient

    def all_for_integration(self) -> QuerySet:
        return self.model.all_objects.all().prefetch_related('profile__users__contacts')

    @classmethod
    def get_slave_relations(cls, patient: Patient) -> QuerySet:
        profile = patient.profile
        relations = Relation.objects.filter(
            master_id=profile.id, can_update_slave_appointments=True
        )
        return relations

    @classmethod
    def get_slave_relations__with_patients(cls, patient: Patient) -> QuerySet:
        relations = cls.get_slave_relations(patient)
        relations = relations.filter(slave__patient__isnull=False)
        return relations

    @classmethod
    def get_slave_related_patients(cls, patient: Patient) -> QuerySet:
        master_relations = cls.get_slave_relations__with_patients(patient)
        slave_profiles = master_relations.values_list('slave_id', flat=True)
        related_profiles = Profile.objects.filter(id__in=slave_profiles)
        related_patients = cls.all().filter(profile__id__in=related_profiles)
        return related_patients
