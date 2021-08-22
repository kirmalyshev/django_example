from typing import Dict

from django.urls import reverse
from rest_framework import status

from apps.appointments.constants import PATIENT_ID
from apps.clinics.factories import PatientUserFactory, PatientFactory
from apps.clinics.models import Patient
from apps.clinics.selectors import PatientSelector
from apps.clinics.test_tools import add_child_relation
from apps.profiles.constants import (
    FIRST_NAME,
    LAST_NAME,
    PATRONYMIC,
    GENDER,
    PROFILE_ID,
    BIRTH_DATE,
    Gender,
    RelationType,
    RELATION_TYPE,
    RELATION_ID,
    FULL_NAME,
    ProfileType,
)
from apps.profiles.factories import ProfileFactory
from apps.profiles.models import User, Profile, Relation
from apps.tools.apply_tests.case import TestCaseCheckStatusCode


def _serialize_single_relation(relation: Relation) -> Dict:
    slave = relation.slave
    return {
        RELATION_ID: relation.id,
        PATIENT_ID: slave.patient.id,
        PROFILE_ID: slave.id,
        RELATION_TYPE: relation.type,
        FULL_NAME: slave.full_name,
        LAST_NAME: slave.last_name,
        FIRST_NAME: slave.first_name,
        PATRONYMIC: slave.patronymic,
        GENDER: slave.gender,
        BIRTH_DATE: slave.birth_date and slave.birth_date.isoformat() or None,
    }


class RelatedPatientListBaseTest(TestCaseCheckStatusCode):
    maxDiff = None
    url = reverse('api.v1:related_patient_list')

    @classmethod
    def setUpTestData(cls):
        cls.master_patient_user: User = PatientUserFactory()
        cls.master_patient: Patient = cls.master_patient_user.patient
        cls.master_profile: Profile = cls.master_patient.profile
        cls.child_patient: Patient = PatientFactory()
        cls.child_patient_profile: Profile = cls.child_patient.profile
        cls.relation_1 = Relation.objects.create(
            master=cls.master_profile,
            slave=cls.child_patient.profile,
            can_update_slave_appointments=True,
        )

    def test_url(self):
        self.assertEqual(self.url, '/api/v1/related_patients')

    def test_anonymous(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.check_status_code(response, status.HTTP_401_UNAUTHORIZED)


class RelatedPatientListViewTest(RelatedPatientListBaseTest):
    def test_get(self):
        self.client.force_login(self.master_patient_user)
        response = self.client.get(self.url)
        self.check_status_code(response, status.HTTP_200_OK)
        actual_data = response.json()['results']
        self.assertEqual(1, len(actual_data))
        expected_data = [_serialize_single_relation(self.relation_1)]
        self.assertEqual(actual_data, expected_data)

    def test_get__no_patient_for_related_profile(self):
        self.client.force_login(self.master_patient_user)
        child_profile: Profile = ProfileFactory(type=ProfileType.PATIENT)
        relation = Relation.objects.create(
            master=self.master_profile, slave=child_profile, can_update_slave_appointments=True,
        )
        response = self.client.get(self.url)
        self.check_status_code(response, status.HTTP_200_OK)
        actual_data = response.json()['results']
        self.assertEqual(1, len(actual_data))
        expected_data = [_serialize_single_relation(self.relation_1)]
        self.assertEqual(actual_data, expected_data)


class RelatedPatientCreateViewTest(RelatedPatientListBaseTest):
    def test_post__ok(self):
        self.client.force_login(self.master_patient_user)
        response = self.client.post(
            self.url,
            data={
                FIRST_NAME: "1",
                PATRONYMIC: "2",
                LAST_NAME: "3",
                GENDER: Gender.MAN,
                BIRTH_DATE: "1988-05-11",
                RELATION_TYPE: RelationType.CHILD,
            },
        )
        self.check_status_code(response, status.HTTP_201_CREATED)
        actual_data = response.json()
        self.assertEqual(
            2, PatientSelector.get_slave_relations__with_patients(self.master_patient).count()
        )

        latest_relation = PatientSelector.get_slave_relations__with_patients(
            self.master_patient
        ).latest("created")
        new_profile = latest_relation.slave
        expected_item = {
            RELATION_ID: latest_relation.id,
            PATIENT_ID: new_profile.patient.id,
            PROFILE_ID: new_profile.id,
            RELATION_TYPE: RelationType.CHILD,
            FULL_NAME: "3 1 2",
            LAST_NAME: "3",
            FIRST_NAME: "1",
            PATRONYMIC: "2",
            GENDER: Gender.MAN,
            BIRTH_DATE: "1988-05-11",
        }
        self.assertEqual(actual_data, expected_item)

        created_patient: Patient = Patient.objects.get(id=actual_data['patient_id'])
        self.assertFalse(created_patient.is_confirmed)


class RelatedPatientViewTest(TestCaseCheckStatusCode):
    maxDiff = None

    def _get_url(self, relation_pk):
        return reverse('api.v1:related_patient_item', kwargs={'pk': relation_pk})

    @classmethod
    def setUpTestData(cls):
        cls.master_patient_user: User = PatientUserFactory()
        cls.master_patient: Patient = cls.master_patient_user.patient
        cls.master_profile: Profile = cls.master_patient.profile
        cls.child_patient: Patient = PatientFactory()
        cls.child_patient_profile: Profile = cls.child_patient.profile
        cls.relation_1 = Relation.objects.create(
            master=cls.master_profile,
            slave=cls.child_patient.profile,
            can_update_slave_appointments=True,
            type=RelationType.OTHER,
        )

    def test_url(self):
        self.assertEqual(self._get_url(100500), '/api/v1/related_patients/100500')

    def test_retrieve__ok(self):
        self.client.force_login(self.master_patient_user)

        response = self.client.get(self._get_url(self.relation_1.pk))
        self.check_status_code(response, status.HTTP_200_OK)
        actual_data = response.json()
        expected = _serialize_single_relation(self.relation_1)
        self.assertEqual(expected, actual_data)

    def test_retrieve__relation_without_patient(self):
        self.client.force_login(self.master_patient_user)
        child_profile: Profile = ProfileFactory(type=ProfileType.PATIENT)
        relation = Relation.objects.create(
            master=self.master_profile, slave=child_profile, can_update_slave_appointments=True,
        )

        response = self.client.get(self._get_url(relation.pk))
        self.check_status_code(response, status.HTTP_404_NOT_FOUND)

    def test_update__put__ok(self):
        self.client.force_login(self.master_patient_user)

        response = self.client.put(
            self._get_url(self.relation_1.pk),
            data={
                # RELATION_ID: self.relation_1.pk,
                FIRST_NAME: "first_ololo",
                LAST_NAME: "last",
                PATRONYMIC: "patr",
                RELATION_TYPE: RelationType.PARENT,
                BIRTH_DATE: "1955-09-13",
                GENDER: Gender.WOMAN,
            },
        )
        self.check_status_code(response, status.HTTP_200_OK)
        actual_data = response.json()
        profile = self.relation_1.slave
        expected = {
            RELATION_ID: self.relation_1.id,
            PATIENT_ID: profile.patient.id,
            PROFILE_ID: profile.id,
            RELATION_TYPE: RelationType.PARENT,
            FULL_NAME: "last first_ololo patr",
            LAST_NAME: "last",
            FIRST_NAME: "first_ololo",
            PATRONYMIC: "patr",
            GENDER: Gender.WOMAN,
            BIRTH_DATE: "1955-09-13",
        }
        self.assertEqual(expected, actual_data)

    def test_update__patch__ok(self):
        self.client.force_login(self.master_patient_user)

        response = self.client.patch(
            self._get_url(self.relation_1.pk), data={FIRST_NAME: "patch_ololo",}
        )
        self.check_status_code(response, status.HTTP_200_OK)
        actual_data = response.json()
        profile = self.relation_1.slave
        expected = {
            RELATION_ID: self.relation_1.id,
            PATIENT_ID: profile.patient.id,
            PROFILE_ID: profile.id,
            RELATION_TYPE: RelationType.OTHER,
            FULL_NAME: f"{profile.last_name} patch_ololo {profile.patronymic}",
            LAST_NAME: profile.last_name,
            FIRST_NAME: "patch_ololo",
            PATRONYMIC: profile.patronymic,
            GENDER: Gender.NOT_SET,
            BIRTH_DATE: None,
        }
        self.assertEqual(expected, actual_data)

    def test_update__patch__fail__no_data_passed(self):
        self.client.force_login(self.master_patient_user)

        response = self.client.patch(self._get_url(self.relation_1.pk), data={})
        self.check_status_code(response, status.HTTP_400_BAD_REQUEST)
        actual_data = response.json()
        self.assertEqual(
            {
                'api_errors': [{'code': 'validation_error', 'title': 'No data passed'}],
                'non_field_errors': ['No data passed'],
            },
            actual_data,
            actual_data,
        )

    def test_delete__ok(self):
        self.client.force_login(self.master_patient_user)
        new_child: Patient = PatientFactory()
        new_relation = Relation.objects.create(
            master=self.master_profile,
            slave=new_child.profile,
            can_update_slave_appointments=True,
            type=RelationType.CHILD,
        )

        response = self.client.delete(self._get_url(new_relation.pk))
        self.check_status_code(response, status.HTTP_204_NO_CONTENT)

        self.assertIsNone(Relation.objects.filter(id=new_relation.pk).first())
