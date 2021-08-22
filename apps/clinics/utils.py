from typing import List

from rest_framework.views import APIView

from apps.clinics.models import Patient
from apps.profiles.models import User
from apps.profiles.permissions import IsPatient


class PatientUtils:
    @classmethod
    def get_slave_patients_ids(cls, patient: Patient) -> List[int]:
        current_profile = patient.profile
        slave_patient_ids = Patient.objects.filter(
            profile__relations__master=current_profile,
            profile__relations__can_update_slave_appointments=True,
        ).values_list('profile__relations__slave__patient', flat=True)
        return list(slave_patient_ids)

    @classmethod
    def get_master_profile_ids(cls, patient: Patient) -> List[int]:
        current_profile = patient.profile
        master_profile_ids = Patient.objects.filter(
            profile__relations__slave=current_profile,
            profile__relations__can_update_slave_appointments=True,
        ).values_list('profile__relations__master', flat=True)

        return list(master_profile_ids)

    @classmethod
    def get_master_user_ids(cls, patient: Patient) -> List[int]:
        profile_ids = cls.get_master_profile_ids(patient)
        user_ids = User.objects.filter(profile__id__in=profile_ids).values_list('id', flat=True)
        return list(user_ids)


class PatientAPIViewMixin(APIView):
    permission_classes = (IsPatient,)

    def _get_author_patient(self) -> Patient:
        return self.request.user.profile.patient
