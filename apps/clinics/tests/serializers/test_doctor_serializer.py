from django.test import TestCase

from apps.clinics.factories import DoctorFactory
from apps.clinics.serializers import DoctorSerializer


class DoctorSerializerTest(TestCase):
    maxDiff = None
    serializer_class = DoctorSerializer

    def test_valid_data(self):
        doctor = DoctorFactory(
            description='эникей 80уровня',
            experience='experince_1',
            education='Средняя школа №100500',
            speciality_text='Коновал',
            youtube_video_link="https://www.youtube.com/watch?v=-r1Q04Qq4so",
        )

        serializer = self.serializer_class(instance=doctor, many=False)
        actual_data = serializer.data
        expected_data = {
            'id': doctor.id,
            'full_name': doctor.profile.full_name,
            'picture': None,
            'description': 'эникей 80уровня',
            'experience': 'experince_1',
            'education': 'Средняя школа №100500',
            'speciality_text': 'Коновал',
            'subsidiaries': [val for val in doctor.subsidiaries.all().values('id', 'title')],
            'services': [val for val in doctor.services.all().values('id', 'title')],
            'is_timeslots_available_for_patient': False,
            "grade": None,
            "youtube_video_id": "-r1Q04Qq4so",
        }
        self.assertEqual(expected_data, actual_data)
