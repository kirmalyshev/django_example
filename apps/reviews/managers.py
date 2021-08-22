from django.db.models import Manager

from apps.appointments.constants import AUTHOR_PATIENT, APPOINTMENT
from apps.clinics.models import Doctor
from apps.core.models import DisplayableQuerySet


class ReviewQuerySet(DisplayableQuerySet):
    def created_by_patient(self, patient_id: int):
        return self.filter(author_patient_id=patient_id)

    def for_appointment(self, appointment_id: int):
        return self.filter(appointment_id=appointment_id)

    def for_doctor(self, doctor: Doctor):
        return self.filter(doctor=doctor)


class ReviewManager(Manager.from_queryset(ReviewQuerySet)):
    def get_queryset(self) -> ReviewQuerySet:
        qs = super(ReviewManager, self).get_queryset()
        return qs.select_related(AUTHOR_PATIENT, APPOINTMENT)
