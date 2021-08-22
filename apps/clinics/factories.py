from typing import Optional

import factory
from django.db.models.signals import post_save, pre_save
from django.utils.dates import WEEKDAYS
from factory import fuzzy
from factory.django import mute_signals

from apps.clinics.models import (
    Doctor,
    Patient,
    Service,
    Subsidiary,
    SubsidiaryWorkday,
    SubsidiaryContact,
    ServicePrice,
)
from apps.profiles.factories import UserFactory, DoctorProfileFactory, PatientProfileFactory
from apps.profiles.models import Profile


@mute_signals(pre_save, post_save)
class SubsidiaryFactory(factory.django.DjangoModelFactory):
    title = factory.Sequence(lambda n: 'subsidiary #{}'.format(n))
    address = factory.Sequence(lambda n: 'subsidiary_address #{}'.format(n))
    short_address = factory.Sequence(lambda n: 'short_address #{}'.format(n))

    class Meta:
        model = Subsidiary
        django_get_or_create = ('title',)


@mute_signals(pre_save, post_save)
class SubsidiaryContactFactory(factory.django.DjangoModelFactory):
    subsidiary = factory.SubFactory(SubsidiaryFactory)
    title = factory.Sequence(lambda n: 'subsdiary contact #{}'.format(n))
    value = fuzzy.FuzzyText(length=25)
    ordering_number = fuzzy.FuzzyInteger(1, 10)

    class Meta:
        model = SubsidiaryContact
        django_get_or_create = ('subsidiary', 'title')


@mute_signals(pre_save, post_save)
class SubsidiaryWorkdayFactory(factory.django.DjangoModelFactory):
    subsidiary = factory.SubFactory(SubsidiaryFactory)
    weekday = fuzzy.FuzzyChoice(WEEKDAYS.values())
    value = 'c 8 до 20:00'
    ordering_number = fuzzy.FuzzyInteger(1, 10)

    class Meta:
        model = SubsidiaryWorkday
        django_get_or_create = ('subsidiary', 'weekday')


@mute_signals(pre_save, post_save)
class ServiceFactory(factory.django.DjangoModelFactory):
    title = factory.Sequence(lambda n: 'service #{}'.format(n))
    description = fuzzy.FuzzyText(length=150)

    class Meta:
        model = Service
        django_get_or_create = ('title',)

    @classmethod
    def _create(cls, model_class, **kwargs):
        old_mptt_updates_enabled = Service._mptt_updates_enabled
        if not kwargs.get('parent'):
            Service._set_mptt_updates_enabled(False)
        obj = super(ServiceFactory, cls)._create(model_class, **kwargs)
        Service._set_mptt_updates_enabled(old_mptt_updates_enabled)
        return obj

    @factory.post_generation
    def subsidiaries(self, create, extracted, **kwargs):
        if not create:
            # Simple build, do nothing.
            return

        if extracted:
            # A list of subsidiaries were passed in, use them
            for subsidiary in extracted:
                self.subsidiaries.add(subsidiary)


@mute_signals(pre_save, post_save)
class ServicePriceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ServicePrice
        django_get_or_create = (
            'service',
            'title',
        )

    service = factory.Iterator(Service.objects.all())
    title = factory.Sequence(lambda n: 'title #{}'.format(n))
    price = factory.Sequence(lambda n: 'price #{}'.format(n))


@mute_signals(pre_save, post_save)
class DoctorFactory(factory.django.DjangoModelFactory):
    profile = factory.SubFactory(DoctorProfileFactory)
    description = fuzzy.FuzzyText(length=150)

    class Meta:
        model = Doctor
        django_get_or_create = ('profile',)

    @factory.post_generation
    def subsidiaries(self, create, extracted, **kwargs):
        if not create:
            # Simple build, do nothing.
            return

        if extracted:
            # A list of subsidiaries were passed in, use them
            for subsidiary in extracted:
                self.subsidiaries.add(subsidiary)

    @factory.post_generation
    def services(self, create, extracted, **kwargs):
        if not create:
            # Simple build, do nothing.
            return

        if extracted:
            # A list of services we passed in, use them
            for service in extracted:
                self.services.add(service)


@mute_signals(pre_save, post_save)
class PatientFactory(factory.django.DjangoModelFactory):
    profile = factory.SubFactory(PatientProfileFactory)

    class Meta:
        model = Patient
        django_get_or_create = ('profile',)


class PatientUserFactory(UserFactory):
    @factory.post_generation
    def patient(self, create: bool, extracted: Optional[Patient], **kwargs) -> Optional[Patient]:
        if not create:
            return

        try:
            existing_patient = self.profile and self.profile.patient
        except Patient.DoesNotExist as err:
            existing_patient = None
        if existing_patient and not extracted:
            return existing_patient

        if extracted:
            patient = extracted
        else:
            patient: Patient = PatientFactory()

        self.profile = patient.profile
        self.save()
        return patient
