from apps.clinics.factories import PatientFactory
from apps.clinics.models import Patient
from apps.profiles.models import Relation


def add_child_relation(master_patient) -> (Patient, Relation):
    child_patient: Patient = PatientFactory()
    relation = Relation.objects.create(
        master=master_patient.profile,
        slave=child_patient.profile,
        can_update_slave_appointments=True,
    )
    return child_patient, relation
