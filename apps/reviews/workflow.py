import logging
from typing import Optional, List

from constance import config as constance_config
from django.conf import settings
from django.core.mail import send_mail
from django.utils.translation import ugettext_lazy as _
from rest_framework.exceptions import ValidationError

from apps.appointments.constants import (
    APPOINTMENT_ID,
    APPOINTMENT__ASK_FOR_REVIEW,
)
from apps.appointments.models import Appointment
from apps.appointments.selectors import PatientAppointments
from apps.appointments.utils import AppointmentUtils
from apps.clinics.constants import PATIENT
from apps.clinics.models import Doctor
from apps.core.admin import get_change_url
from apps.core.utils import make_absolute_url
from apps.notify import send_event
from apps.notify.constants import PUSH
from apps.reviews.constants import ReviewStatus, GRADE
from apps.reviews.models import Review
from apps.reviews.selectors import ReviewSelector
from apps.reviews.tools import is_adding_review_allowed


class ReviewValidator:
    @classmethod
    def validate_review_text(cls, text):
        pass

    @classmethod
    def validate_create_data(cls, data: dict) -> dict:
        appointment_id = data['appointment_id']
        patient = data.get('patient')
        text = data.get('text')
        grade = data.get('grade')
        appointment: Optional[Appointment] = PatientAppointments(patient).all().filter(
            id=appointment_id
        ).first()
        if not appointment:
            raise ValidationError(_("No appointment found for passed appointment_id"))

        if ReviewSelector.created_by_patient(patient).for_appointment(appointment_id).exists():
            raise ValidationError(_("Вы уже отправили отзыв по этой записи на прием"))
        cls.validate_review_text(text)
        if not appointment.doctor_id:
            err = ValidationError(
                _(
                    "Для этой записи не указан доктор. Мы уже знаем о проблеме, решим в ближайшее время."
                )
            )
            logging.error(err, extra={APPOINTMENT_ID: appointment_id, "create_data": data})
            raise err

        data['doctor_id'] = appointment.doctor_id
        return data


class ReviewWorkflow:
    model = Review
    validator = ReviewValidator

    @classmethod
    def ask_for_appointment_review(cls, appointment: Appointment):
        if not is_adding_review_allowed(appointment):
            return
        doctor_and_date = ""
        doctor_short_name = appointment.doctor.short_full_name
        if doctor_short_name:
            doctor_and_date = f"Специалист: {doctor_short_name}"
        if appointment.start:
            doctor_and_date += f"\nДата: {appointment.start_date_tz_formatted__short} {appointment.start_time_tz_formatted }"
        if doctor_and_date:
            doctor_and_date += "\n"
        event_context = {
            APPOINTMENT_ID: appointment.id,
            PATIENT: appointment.patient.short_full_name,
            "doctor_and_date": doctor_and_date,
        }

        user_ids = AppointmentUtils.get_user_ids_to_notify(appointment)
        for receiver_user_id in user_ids:
            params = dict(
                event_name=APPOINTMENT__ASK_FOR_REVIEW,
                user_id=receiver_user_id,
                channel=PUSH,
                appointment_id=appointment.id,
                context=event_context,
            )
            send_event(**params)

    @classmethod
    def create_by_patient(cls, patient, data) -> model:
        data['patient'] = patient
        data = cls.validator.validate_create_data(data)

        doctor_id = data['doctor_id']
        appointment_id = data.get('appointment_id')
        text = data['text']
        grade = data['grade']

        review = cls.model.objects.create(
            grade=grade,
            author_patient=patient,
            doctor_id=doctor_id,
            appointment_id=appointment_id,
            text=text,
            is_displayed=False,
            status=ReviewStatus.NEW,
        )
        cls.notify_staff_about_new_review(review)

        return review

    @classmethod
    def notify_staff_about_new_review(cls, review: Review) -> None:
        emails: str = constance_config.REVIEWS_NOTIFICATION_EMAILS
        if not emails:
            return

        email_list: List[str] = emails.split()

        obj_url = make_absolute_url(get_change_url(review))
        subject = f'{settings.SHORT_PREFIX}: Новый отзыв'
        message = (
            f"Оценка: {review.grade}\n"
            f"Текст отзыва: {review.text}\n"
            f"Дата приема: {review.appointment.human_start_datetime}\n"
            f"Доктор: {review.doctor}"
            f"\nСсылка на отзыв в админке: {obj_url}"
        )
        send_mail(subject, message, settings.SYSTEM_SENDER_EMAIL, email_list)

    @classmethod
    def get_actual_grade_for_doctor(cls, doctor: Doctor) -> Optional[float]:
        displayed_reviews = doctor.review_set.all().displayed()
        if not displayed_reviews.exists():
            return
        grades = displayed_reviews.values_list(GRADE, flat=True)

        actual_grade = round(sum(grades) / len(grades), 1)
        return actual_grade
