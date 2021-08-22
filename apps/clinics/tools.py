import logging
import random
from datetime import timedelta
from typing import Optional, List

from constance import config as constance_config
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from apps.appointments.factories import _generate_valid_time_slot_start_end, TimeSlotFactory
from apps.clinics.factories import SubsidiaryFactory
from apps.clinics.models import Doctor, Patient
from apps.core.admin import get_change_url
from apps.core.utils import make_absolute_url


def create_random_month_slots_for_doctor(doctor: Doctor):
    subsidiary_titles = doctor.subsidiaries.all().values_list('title', flat=True)
    if not subsidiary_titles:
        subsidiary = SubsidiaryFactory()
    else:
        subsidiary = SubsidiaryFactory(title=random.choice(subsidiary_titles))

    now = timezone.now()
    for i in range(1, 31):
        initial = now + timedelta(days=i)
        for j in range(5):
            start, end = _generate_valid_time_slot_start_end(initial, doctor)
            if start and end:
                TimeSlotFactory.create(
                    doctor=doctor, subsidiary=subsidiary, start=start, end=end,
                )


def send_email_about_merged_patients(parient_from, patient_to, actor: Optional[str] = None):
    emails_str: str = constance_config.PATIENT_INTEGRATION_UPDATE_EMAILS
    if not emails_str:
        return
    emails: List[str] = emails_str.split(" ")

    subject = f"Объединились пациенты на {settings.SHORT_PREFIX}"

    text = f"""<br />
    Данные из пациента <a href="{make_absolute_url(get_change_url(parient_from))}">{parient_from}</a>
    <br />
    были импортированы в пациента <a href="{make_absolute_url(get_change_url(patient_to))}">{patient_to}</a> <br />
    Проверьте, пожалуйста, что объединение было корректным
    """
    try:
        send_mail(
            subject,
            text,
            settings.SYSTEM_SENDER_EMAIL,
            emails,
            html_message=text,
            fail_silently=True,
        )
    except Exception as err:
        logging.exception(err,)


def get_patient_related_object_ids(patient: Patient) -> set:
    ids = [patient.id]
    if patient.profile_id:
        profile = patient.profile
        ids.append(patient.profile_id)
        ids.extend(profile.groups.all().values_list("id", flat=True))
        master_ids = profile.relations.all().values_list("master_id", flat=True)
        slave_ids = profile.relations.all().values_list("slave_id", flat=True)
        ids.extend(master_ids)
        ids.extend(slave_ids)
    if patient.user:
        user = patient.user
        ids.append(user.id)
        ids.extend(user.ordered_contacts.all().values_list("id", flat=True))

    return set(ids)
