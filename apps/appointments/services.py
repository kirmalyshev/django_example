from typing import Dict

from apps.appointments.models import Appointment


def create_appointment(*, model_data: Dict) -> Appointment:
    appointment = Appointment(**model_data)
    appointment.full_clean()
    appointment.save()

    return appointment
