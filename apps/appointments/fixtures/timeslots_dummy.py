from sys import stdout

from apps.clinics.selectors import ServiceSelector, DoctorSelector
from apps.clinics.tools import create_random_month_slots_for_doctor


def load():
    doctors = DoctorSelector.all().without_hidden()
    if not doctors.exists():
        stdout.write(
            "\nError: Cannot create TimeSlots - there're no doctors in DB. "
            "You can create doctors with fixture apps.clinics.fixtures.doctors_dummy\n"
        )
        return
    services = ServiceSelector.all()
    if not doctors.exists():
        stdout.write(
            "\nError: Cannot create TimeSlots - there're no doctors in DB. "
            "You can create doctors with fixture apps.clinics.fixtures.doctors_dummy\n"
        )
        return
    for doctor in doctors.iterator():
        create_random_month_slots_for_doctor(doctor)
