import random

from apps.clinics.factories import DoctorFactory, SubsidiaryFactory
from apps.clinics.fixtures.subsidiaries_dummy import subsidiary_titles

DEPENDS_ON = ['apps.clinics.fixtures.subsidiaries_dummy']


def load():
    for i in range(10):
        DoctorFactory(subsidiaries=[SubsidiaryFactory(title=random.choice(subsidiary_titles))])
