from apps.clinics.factories import PatientUserFactory


def load():
    PatientUserFactory.create_batch(size=10)
