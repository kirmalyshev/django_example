from typing import Dict, Union

import logging
from django.core.exceptions import ValidationError as DjangoValidationError, ObjectDoesNotExist
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from drf_yasg.utils import swagger_serializer_method
from rest_framework import serializers

from apps.appointments import models
from apps.appointments.constants import (
    RELATED_PATIENT_FULL_NAME,
    ADDITIONAL_NOTES,
    IS_FOR_WHOLE_DAY,
    HUMAN_START,
    START,
    HUMAN_WEEKDAY,
    DOCTOR,
    SERVICE,
    SUBSIDIARY,
    PATIENT_ID,
    DOCTOR_ID,
    END,
    HUMAN_START_TIME,
    PATIENT_FULL_NAME,
    HUMAN_START_DATE_SHORT,
    HUMAN_START_DATE,
    SUBSIDIARY_ID,
    SERVICE_ID,
    TIME_SLOT_ID,
    TARGET_PATIENT_ID,
    HUMAN_START_DATETIME,
)
from apps.appointments.model_utils import validate_appointment_start_end
from apps.appointments.models import TimeSlot
from apps.appointments.validators import AppointmentValidator
from apps.clinics.selectors import (
    DoctorSelector,
    SubsidiarySelector,
    ServiceSelector,
    PatientSelector,
)
from apps.clinics.serializers import (
    SubsidiaryForAppointmentSerializer,
    DoctorForAppointmentSerializer,
    ServiceForAppointmentSerializer,
)
from apps.core.serializers import DateTimeTzAwareField
from apps.feature_toggles.ops_features import is_related_patients_enabled
from apps.reviews.selectors import ReviewSelector
from apps.reviews.serializers import ReviewForAppointmentSerializer


class AppointmentStatusSerializer(serializers.Serializer):
    code = serializers.IntegerField(source='status')
    value = serializers.CharField(source='get_status_display')


class AppointmentResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.AppointmentResult
        read_only_fields = fields = (
            'id',
            'created',
            'complaints',
            'diagnosis',
            'recommendations',
        )


class AppointmentSerializer(serializers.ModelSerializer):
    doctor = DoctorForAppointmentSerializer()
    service = ServiceForAppointmentSerializer()
    subsidiary = SubsidiaryForAppointmentSerializer()
    start = DateTimeTzAwareField()
    end = DateTimeTzAwareField()
    human_start = serializers.CharField(source="human_start_tz", read_only=True, required=False)
    human_start_date = serializers.CharField(read_only=True, required=False)
    human_start_date_short = serializers.CharField(
        source="start_date_tz_formatted__short", read_only=True, required=False
    )
    human_start_datetime = serializers.CharField(read_only=True, required=False)
    human_weekday = serializers.CharField(read_only=True, required=False)
    status = serializers.SerializerMethodField(read_only=True)
    is_cancel_by_patient_available = serializers.BooleanField(read_only=True)
    result = serializers.SerializerMethodField(read_only=True, required=False)
    patient_full_name = serializers.CharField(source='patient.profile.full_name')
    reviews = serializers.SerializerMethodField(read_only=True, required=False,)

    @swagger_serializer_method(serializer_or_field=AppointmentStatusSerializer)
    def get_status(self, obj: models.Appointment) -> dict:
        return AppointmentStatusSerializer(obj).data

    @swagger_serializer_method(serializer_or_field=AppointmentResultSerializer)
    def get_result(self, obj: models.Appointment) -> Union[dict, None]:
        if not obj.is_finished:
            return
        try:
            obj.result
        except ObjectDoesNotExist:
            return
        return AppointmentResultSerializer(obj.result).data

    @swagger_serializer_method(serializer_or_field=ReviewForAppointmentSerializer)
    def get_reviews(self, obj: models.Appointment):
        reviews = ReviewSelector.filter_by_appointment_id(appointment_id=obj.id)
        data = ReviewForAppointmentSerializer(reviews, many=True).data
        return data

    class Meta:
        model = models.Appointment
        read_only_fields = fields = (
            'id',
            'created',
            START,
            HUMAN_START,
            HUMAN_START_DATE,
            HUMAN_START_DATETIME,
            HUMAN_START_DATE_SHORT,
            HUMAN_WEEKDAY,
            HUMAN_START_TIME,
            END,
            PATIENT_ID,
            PATIENT_FULL_NAME,
            DOCTOR,
            SERVICE,
            SUBSIDIARY,
            'price',
            'status',
            'reason_text',
            'is_payment_enabled',
            'is_cancel_by_patient_available',
            'is_archived',
            'is_finished',
            'result',
            'has_timeslots',
            'reviews',
            ADDITIONAL_NOTES,
            IS_FOR_WHOLE_DAY,
        )


class AppointmentListSerializer(AppointmentSerializer):
    grade = serializers.SerializerMethodField(read_only=True, required=False)
    related_patient_full_name = serializers.SerializerMethodField(read_only=True, required=False)

    @swagger_serializer_method(serializer_or_field=serializers.IntegerField)
    def get_grade(self, obj: models.Appointment):
        patient_reviews = ReviewSelector.created_by_patient(patient_id=obj.patient_id)
        reviews = ReviewSelector.filter_by_appointment_id(
            appointment_id=obj.id, queryset=patient_reviews
        )
        if not reviews.exists():
            return
        grades = reviews.values_list('grade', flat=True)
        return grades[0]

    @swagger_serializer_method(serializer_or_field=serializers.CharField)
    def get_related_patient_full_name(self, obj: models.Appointment):
        request = self.context.get('request')
        if not request:
            return ""

        current_patient = request.user.profile.patient
        if obj.patient_id == current_patient.id:
            return ""
        return obj.patient.full_name

    class Meta(AppointmentSerializer.Meta):
        read_only_fields = fields = (
            'id',
            START,
            HUMAN_START,
            HUMAN_START_DATE,
            HUMAN_START_DATETIME,
            HUMAN_START_DATE_SHORT,
            HUMAN_WEEKDAY,
            HUMAN_START_TIME,
            END,
            PATIENT_ID,
            DOCTOR_ID,
            DOCTOR,
            SERVICE,
            SUBSIDIARY,
            'status',
            'reason_text',
            'is_payment_enabled',
            'is_cancel_by_patient_available',
            'is_archived',
            'is_finished',
            'price',
            'has_timeslots',
            'grade',
            RELATED_PATIENT_FULL_NAME,
            IS_FOR_WHOLE_DAY,
        )


class BaseAppointmentCreateSerializer(serializers.ModelSerializer):
    start = serializers.DateTimeField(
        required=False,
        # input_formats=[APPOINTMENT_DATETIME_FORMAT],
        default_timezone=timezone.utc,
    )
    end = serializers.DateTimeField(
        required=False,
        # input_formats=[APPOINTMENT_DATETIME_FORMAT],
        default_timezone=timezone.utc,
    )
    time_slot_id = serializers.IntegerField(required=False)

    def validate_time_slot_id(self, time_slot_id: int):
        if not TimeSlot.objects.filter(id=time_slot_id).exists():
            raise serializers.ValidationError(_('TimeSlot does not exist'))
        return time_slot_id

    class Meta:
        model = models.Appointment

    def validate_start(self, start_value: timezone.datetime) -> timezone.datetime:
        now = timezone.now()
        now = timezone.localtime(now)
        if start_value <= now:
            raise serializers.ValidationError(_('Время начала записи должно быть в будущем'))
        return start_value

    def validate_end(self, end_value: timezone.datetime) -> timezone.datetime:
        now = timezone.now()
        if end_value.astimezone(timezone.utc) <= now:
            raise serializers.ValidationError(_('Время окончания записи должно быть в будущем'))
        return end_value

    def validate(self, attrs: Dict) -> Dict:
        data = super(BaseAppointmentCreateSerializer, self).validate(attrs)
        start = data.get("start")
        end = data.get("end")
        time_slot_id = data.get("time_slot_id")
        if not (start and end) and not time_slot_id:
            raise serializers.ValidationError("Must be set `time_slot_id`,  or `start/end`")

        try:
            validate_appointment_start_end(start, end)
        except DjangoValidationError as err:
            raise serializers.ValidationError(err)
        return data


class CreateAppointmentRequestSerializer(BaseAppointmentCreateSerializer):
    doctor_id = serializers.IntegerField(required=False)
    subsidiary_id = serializers.IntegerField(required=False)
    service_id = serializers.IntegerField(required=False)
    reason_text = serializers.CharField(required=False)
    target_patient_id = serializers.IntegerField(required=False, min_value=1)

    class Meta(BaseAppointmentCreateSerializer.Meta):
        fields = (
            'start',
            'end',
            'target_patient_id',
            'doctor_id',
            'subsidiary_id',
            'service_id',
            'time_slot_id',
            'reason_text',
        )

    def validate_doctor_id(self, doctor_id: int) -> int:
        if not DoctorSelector.all().filter(id=doctor_id).exists():
            raise serializers.ValidationError(_('Doctor does not exist'))
        return doctor_id

    def validate_subsidiary_id(self, subsidiary_id):
        if not SubsidiarySelector.all().filter(id=subsidiary_id).exists():
            raise serializers.ValidationError(_('Subsidiary does not exist'))
        return subsidiary_id

    def validate_service_id(self, service_id):
        if not ServiceSelector().all().filter(id=service_id).exists():
            raise serializers.ValidationError(_('Service does not exist'))
        return service_id

    def validate_target_patient_id(self, target_patient_id: int):
        if not is_related_patients_enabled.is_enabled:
            err = serializers.ValidationError(_('Param is not expected due to inner settings'))
            logging.error(f"Invalid behavior for target_patient_id: {err}")
            raise err

        if not PatientSelector.get_or_none(target_patient_id):
            raise serializers.ValidationError(_('Patient does not exist'))
        return target_patient_id

    def validate(self, attrs):
        print(f"CreateAppointmentRequestSerializer.validate {attrs=}")
        AppointmentValidator.validate_create_data(attrs)
        return attrs


class MixedAppointmentListSerializer(serializers.Serializer):
    appointments = AppointmentListSerializer(read_only=True, many=True)
    appointment_requests = serializers.Serializer(read_only=True, many=True)

    class Meta:
        fields = ('appointments', 'appointment_requests')


class TimeSlotSerializer(serializers.ModelSerializer):
    start = DateTimeTzAwareField()
    end = DateTimeTzAwareField()

    class Meta:
        model = models.TimeSlot
        fields = read_only_fields = [
            'id',
            DOCTOR_ID,
            SUBSIDIARY_ID,
            'is_available',
            START,
            'duration',
            END,
        ]


class TimeSlotDateSerializer(serializers.Serializer):
    start_date = serializers.DateField(read_only=True)
