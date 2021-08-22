from apps.exceptions import APIError


class RelatedPatientCreateError(APIError):
    code = 'related_patient_create_error'
    title = 'RelatedPatientCreateError'
    details = None
