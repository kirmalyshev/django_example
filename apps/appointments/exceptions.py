from apps.exceptions import APIError


class AppointmentError(APIError):
    code = 'appointment_error'
    title = 'AppointmentError'
    details = None


class WrongStatusError(APIError):
    code = 'wrong_status_error'


class AppointmentCreateError(AppointmentError):
    code = 'appointment_create_error'


class AppointmentRejectError(AppointmentError):
    code = 'appointment_reject_error'


class AppointmentApproveError(AppointmentError):
    code = 'appointment_approve_error'


class AppointmentWrongStatusError(AppointmentError):
    code = 'appointment__wrong_status_error'


class AppointmentWrongOwnerError(AppointmentError):
    code = 'appointment__wrong_owner'


class TooManyNearbyAppointments(APIError):
    code = 'too_many_nearby_appointments'


class TimeSlotError(APIError):
    pass


class NoStartEndValuesError(TimeSlotError):
    pass
