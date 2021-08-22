import logging
from typing import List

from asgiref.sync import async_to_sync
from django.db import transaction

from apps.clinics.constants import INTEGRATION_DATA
from apps.clinics.data_models import RelatedPatientCreateData, RelatedPatientUpdateData
from apps.clinics.exceptions import RelatedPatientCreateError
from apps.clinics.models import Patient
from apps.clinics.selectors import PatientSelector
from apps.clinics.tools import send_email_about_merged_patients
from apps.integration.constants import PatientItemDict, MIS_SUBSIDIARY_ID, EXTRA_SUBSIDIARY_INFO
from apps.integration.get_workflow import get_integration_workflow
from apps.profiles.constants import (
    LAST_NAME,
    ProfileType,
    PATRONYMIC,
    FIRST_NAME,
    BIRTH_DATE,
    GENDER,
)
from apps.profiles.models import ProfileGroup, Relation, Profile


class PatientWorkflow:
    @classmethod
    def merge_patients(cls, patient_from: Patient, patient_to: Patient, **kwargs) -> Patient:
        logging.debug(f'merge {patient_from=} ==> {patient_to=} ...')
        move_profile_groups = kwargs.get("move_profile_groups", False)
        delete_patient_from = kwargs.get("delete_patient_from", False)
        replace_integration_data: bool = kwargs.get("replace_integration_data", False)
        load_old_appointments: bool = kwargs.get("load_old_appointments", True)

        if not patient_to.integration_data or replace_integration_data:
            patient_to.integration_data = patient_from.integration_data
            patient_to.save(update_fields=[INTEGRATION_DATA])
            patient_from.integration_data = {}
            patient_from.save(update_fields=[INTEGRATION_DATA])
        else:
            from_extra_info = patient_from.integration_data.get(EXTRA_SUBSIDIARY_INFO)
            to_extra_info = patient_from.integration_data.get(EXTRA_SUBSIDIARY_INFO)
            for item in from_extra_info:
                to_extra_info.append(item)
            patient_to.integration_data[EXTRA_SUBSIDIARY_INFO] = to_extra_info
            patient_to.save(update_fields=[INTEGRATION_DATA])

            patient_from.integration_data = {}
            patient_from.save(update_fields=[INTEGRATION_DATA])
        # logging.debug(f"integration data updated: {patient_to.integration_data=}")

        appointments = patient_from.appointment_set.all()
        appointments.update(patient=patient_to)
        # logging.debug(f"appointments updated")

        if patient_from.is_confirmed and not patient_to.is_confirmed:
            cls.confirm_patient(patient_to, select_old_appointments=load_old_appointments)

        if move_profile_groups:
            profile_from = patient_from.profile
            profile_to = patient_to.profile
            groups_from = profile_from.groups.all()
            for g in groups_from:
                g: ProfileGroup
                if profile_to not in g.profiles.all():
                    g.profiles.add(profile_to)
                    g.profiles.remove(profile_from)
                    g.save()

        if delete_patient_from is True:
            patient_from.is_confirmed = False
            patient_from.delete(soft=True)
        try:
            send_email_about_merged_patients(
                parient_from=patient_from, patient_to=patient_to,
            )
        except Exception as err:
            logging.error(err)

        return patient_to

    @classmethod
    def confirm_patient(cls, patient: Patient, **kwargs) -> None:
        if patient.is_confirmed:
            return
        patient.is_confirmed = True
        patient.save()

        # select all old appointments from MIS, if possible
        select_old_appointments = kwargs.get("select_old_appointments", False)
        if select_old_appointments:
            cls.load_patient_appointments_from_medical_center(patient=patient)

    @classmethod
    def load_patient_appointments_from_medical_center(cls, patient: Patient, **kwargs):
        integration_workflow = get_integration_workflow()
        if not integration_workflow:
            return

        related_patients = PatientSelector.get_slave_related_patients(patient=patient)
        needed_ids = [patient.id] + list(related_patients.values_list('id', flat=True))
        needed_patients = PatientSelector.all().filter(id__in=needed_ids)
        logging.debug(f"{len(needed_patients)=}")
        logging.debug(f"{needed_patients=}")

        for patient in needed_patients.iterator():
            integration_info_items: List[PatientItemDict] = patient.integration_data.get(
                "extra_subsidiary_info"
            )
            if not integration_info_items:
                continue
            for item in integration_info_items:
                item: PatientItemDict
                mis_patient_id = item.get("patient_id")
                subsidiary_id = item.get("subsidiary_id")
                if mis_patient_id and subsidiary_id:
                    integration_workflow.select_patient_appointments_from_mis(
                        **{"mis_patient_id": mis_patient_id, MIS_SUBSIDIARY_ID: subsidiary_id},
                    )


class RelatedPatientsWorkflow:
    @classmethod
    @transaction.atomic
    def create_related_patient(
        cls, author_patient: Patient, new_patient_data: RelatedPatientCreateData
    ) -> (Relation, Patient):
        # existing_slave_relations = PatientSelector.get_slave_relations(patient=author_patient)
        existing_slave_patients = PatientSelector.get_slave_related_patients(patient=author_patient)

        if existing_slave_patients.filter(
            profile__last_name=new_patient_data['last_name'],
            profile__first_name=new_patient_data['first_name'],
            profile__patronymic=new_patient_data['patronymic'],
            profile__birth_date=new_patient_data['birth_date'],
            profile__gender=new_patient_data['gender'],
        ).exists():
            raise RelatedPatientCreateError(
                "Такой пациент уже есть среди ваших связанных пациентов"
            )

        new_profile = Profile.objects.create(
            last_name=new_patient_data['last_name'],
            first_name=new_patient_data['first_name'],
            patronymic=new_patient_data['patronymic'],
            birth_date=new_patient_data['birth_date'],
            gender=new_patient_data['gender'],
            type=ProfileType.PATIENT,
        )
        new_patient = Patient.objects.create(profile=new_profile, is_confirmed=False)
        new_relation = Relation.objects.create(
            master=author_patient.profile,
            slave=new_profile,
            can_update_slave_appointments=True,
            type=new_patient_data['type'],
        )
        return new_relation, new_patient

    @classmethod
    @transaction.atomic
    def update_related_patient(
        cls,
        author_patient: Patient,
        relation: Relation,
        related_patient_data: RelatedPatientUpdateData,
    ) -> (Relation, Patient):
        # relation: Relation = Relation.objects.get(id=related_patient_data['id'])

        # region update Profile
        slave_profile: Profile = relation.slave
        should_save: bool = False
        for key in (GENDER, BIRTH_DATE, LAST_NAME, FIRST_NAME, PATRONYMIC):
            new_value = related_patient_data.get(key)
            old_value = getattr(slave_profile, key, None)
            if new_value and new_value != old_value:
                should_save = True
                setattr(slave_profile, key, new_value)

        if should_save:
            slave_profile.save()
        # endregion
        new_relation_type = related_patient_data.get("type")
        if new_relation_type and new_relation_type != relation.type:
            relation.type = new_relation_type
            relation.save()

        patient = slave_profile.patient

        return relation, patient
