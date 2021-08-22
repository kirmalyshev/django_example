from apps.clinics.fixtures.clinics_dummy import load as load_clinics
from apps.clinics.fixtures.doctors_dummy import load as doctors_load


def load():
    doctors_load()
