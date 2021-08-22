from collections import OrderedDict

from django.utils.dates import WEEKDAYS

from apps.clinics.factories import SubsidiaryWorkdayFactory, SubsidiaryContactFactory
from apps.clinics.models import Subsidiary

SUBSIDIARY_CONTACTS = {'Регистратура': '+7 999 888 77 66', 'Главный врач': '+7 111 222 33 44'}


def load():
    WorkdayF = SubsidiaryWorkdayFactory
    for subsidiary in Subsidiary.objects.all():
        if subsidiary.workdays.all().exists():
            continue
        for number, weekday in OrderedDict(WEEKDAYS).items():
            WorkdayF(
                subsidiary=subsidiary,
                weekday=weekday,
                value='c 8 до 20:00',
                ordering_number=number + 1,
            )

    ContactF = SubsidiaryContactFactory
    for subsidiary in Subsidiary.objects.all():
        if subsidiary.contacts.all().exists():
            continue

        for title, value in SUBSIDIARY_CONTACTS.items():
            ContactF(subsidiary=subsidiary, title=title, value=value)
