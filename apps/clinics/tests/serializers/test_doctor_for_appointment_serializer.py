from django.test import TestCase

from apps.clinics.factories import DoctorFactory
from apps.clinics.serializers import DoctorForAppointmentSerializer


class DoctorForAppointmentSerializerTest(TestCase):
    maxDiff = None
    serializer_class = DoctorForAppointmentSerializer

    def test_valid_data(self):
        doctor = DoctorFactory(description='эникей 81уровня', speciality_text='ваш лучший друг')

        serializer = self.serializer_class(instance=doctor, many=False)
        actual_data = serializer.data
        expected_data = {
            'id': doctor.id,
            'full_name': doctor.profile.full_name,
            'description': 'эникей 81уровня',
            'speciality_text': 'ваш лучший друг',
            'picture': doctor.profile.picture_draft,
            'is_timeslots_available_for_patient': False,
        }
        self.assertEqual(expected_data, actual_data)
