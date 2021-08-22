from django.conf import settings
from rest_framework import serializers
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.clinics import models
from apps.core.models import DisplayableQuerySet
from apps.profiles.constants import RelationType, Gender
from apps.profiles.validators import validate_birth_date
from apps.reviews.workflow import ReviewWorkflow


class ClinicImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ClinicImage
        fields = ('image',)


class ClinicInfoSerializer(serializers.Serializer):
    images = ClinicImageSerializer(read_only=True, many=True)
    text = serializers.CharField(read_only=True)
    empty_appointment_text = serializers.CharField(read_only=True)


class SubsidiaryImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.SubsidiaryImage
        fields = ('picture', 'priority', 'is_primary')


class SubsidiaryContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.SubsidiaryContact
        fields = ('title', 'value', 'ordering_number')


class SubsidiaryWorkdaySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.SubsidiaryWorkday
        fields = ('weekday', 'value', 'ordering_number')


class SubsidiarySerializer(serializers.ModelSerializer):
    picture = serializers.ImageField(source='primary_image')  # backwards compatibility
    primary_image = serializers.ImageField()
    images = SubsidiaryImageSerializer(many=True, read_only=True)
    contacts = SubsidiaryContactSerializer(many=True, read_only=True)
    workdays = SubsidiaryWorkdaySerializer(many=True, read_only=True)

    class Meta:
        model = models.Subsidiary
        fields = read_only_fields = (
            'id',
            'title',
            'description',
            'address',
            'short_address',
            'latitude',
            'longitude',
            'picture',
            'primary_image',
            'images',
            'contacts',
            'workdays',
        )


class SubsidiaryListSerializer(SubsidiarySerializer):
    class Meta(SubsidiarySerializer.Meta):
        fields = read_only_fields = (
            'id',
            'title',
            'description',
            'address',
            'short_address',
            'latitude',
            'longitude',
            'picture',
            'primary_image',
            'contacts',
            'workdays',
        )


class SubsidiaryForDoctorSerializer(SubsidiarySerializer):
    class Meta(SubsidiarySerializer.Meta):
        fields = read_only_fields = ('id', 'title')


class SubsidiaryForServiceSerializer(SubsidiarySerializer):
    class Meta(SubsidiarySerializer.Meta):
        fields = read_only_fields = ('id', 'title', 'primary_image', 'address', 'short_address')


class SubsidiaryForAppointmentSerializer(SubsidiarySerializer):
    class Meta(SubsidiarySerializer.Meta):
        fields = read_only_fields = (
            'id',
            'title',
            'address',
            'short_address',
            'latitude',
            'longitude',
        )


class SubsidiaryForPromotionSerializer(SubsidiarySerializer):
    class Meta(SubsidiarySerializer.Meta):
        fields = read_only_fields = (
            'id',
            'title',
            'primary_image',
            'address',
            'short_address',
            'latitude',
            'longitude',
        )


class ServicePriceDisplayedListSerializer(serializers.ListSerializer):
    def to_representation(self, data: DisplayableQuerySet):
        data = data.displayed()
        return super(ServicePriceDisplayedListSerializer, self).to_representation(data)


class ServicePriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ServicePrice
        fields = ('title', 'price')
        list_serializer_class = ServicePriceDisplayedListSerializer


class ServiceSerializer(serializers.ModelSerializer):
    subsidiaries = SubsidiaryForServiceSerializer(many=True, read_only=True)
    parent_id = serializers.IntegerField(read_only=True)
    prices = ServicePriceSerializer(many=True, read_only=True,)
    children_count = serializers.SerializerMethodField(read_only=True)

    def get_children_count(self, obj: models.Service) -> int:
        count = obj.get_children().displayed().count()
        return count

    class Meta:
        model = models.Service
        fields = (
            'id',
            'title',
            'description',
            'level',
            'parent_id',
            'children_count',
            'priority',
            'subsidiaries',
            'prices',
            'is_visible_for_appointments',
        )


class ServiceForDoctorSerializer(ServiceSerializer):
    class Meta(ServiceSerializer.Meta):
        fields = (
            'id',
            'title',
            'level',
            'prices',
            'is_visible_for_appointments',
        )


class ServiceForDoctorListSerializer(ServiceForDoctorSerializer):
    class Meta(ServiceForDoctorSerializer.Meta):
        fields = (
            'id',
            'title',
            'level',
            'is_visible_for_appointments',
        )


class ServiceForAppointmentSerializer(ServiceSerializer):
    class Meta(ServiceSerializer.Meta):
        fields = read_only_fields = ('id', 'title')


class BaseDoctorSerializer(serializers.ModelSerializer):
    # full_name = serializers.CharField()
    picture = serializers.ImageField(source='profile.picture_draft')
    services = ServiceForDoctorSerializer(many=True, read_only=True)
    subsidiaries = SubsidiaryForDoctorSerializer(many=True, read_only=True)
    grade = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = models.Doctor
        fields = (
            'id',
            'full_name',
            'picture',
            'description',
            'experience',
            'education',
            'speciality_text',
            'services',
            'subsidiaries',
            'integration_data',
            'is_timeslots_available_for_patient',
            "grade",
        )

    def get_grade(self, obj) -> str:
        value = ReviewWorkflow.get_actual_grade_for_doctor(doctor=obj)
        if value:
            return str(value)


class DoctorSerializer(BaseDoctorSerializer):
    class Meta(BaseDoctorSerializer.Meta):
        fields = (
            'id',
            'full_name',
            'picture',
            'description',
            'experience',
            'education',
            'speciality_text',
            'services',
            'subsidiaries',
            'is_timeslots_available_for_patient',
            "grade",
            "youtube_video_id",
        )


class DoctorListSerializer(BaseDoctorSerializer):
    services = ServiceForDoctorListSerializer(many=True, read_only=True)

    class Meta(BaseDoctorSerializer.Meta):
        fields = (
            'id',
            'full_name',
            'picture',
            'description',
            'experience',
            'education',
            'speciality_text',
            'services',
            'subsidiaries',
            'is_timeslots_available_for_patient',
            "grade",
        )


class DoctorForAppointmentSerializer(BaseDoctorSerializer):
    class Meta(BaseDoctorSerializer.Meta):
        model = models.Doctor
        fields = (
            'id',
            'full_name',
            'description',
            'picture',
            'speciality_text',
            'is_timeslots_available_for_patient',
        )


class PatientSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='profile__full_name')

    class Meta:
        model = models.Patient
        fields = (
            'id',
            'full_name',
            'integration_data',
        )


class PromotionSerializer(serializers.ModelSerializer):
    subsidiaries = SubsidiaryForPromotionSerializer(many=True, read_only=True)

    class Meta:
        model = models.Promotion
        fields = read_only_fields = (
            'id',
            'title',
            'content',
            'subsidiaries',
            'published_from',
            'published_until',
            'publication_range_text',
            'primary_image',
        )


class PromotionFilterSerializer(serializers.Serializer):
    subsidiary_ids = serializers.ListField(
        required=False, child=serializers.IntegerField(min_value=1)
    )


class ApplicationIdsSerializer(serializers.Serializer):
    android = serializers.CharField(default=settings.GCM_DEFAULT_APPLICATION_ID)
    ios = serializers.CharField(default=settings.APNS_DEFAULT_APPLICATION_ID)


class ApplicationConfigSerializer(serializers.Serializer):
    application_ids = ApplicationIdsSerializer(read_only=True)


class RelatedPatientSerializer(serializers.Serializer):
    relation_id = serializers.IntegerField(required=False, read_only=False, source="id")
    patient_id = serializers.IntegerField(required=False, read_only=True, source="slave.patient.id")
    profile_id = serializers.IntegerField(required=False, read_only=False, source="slave_id")
    relation_type = serializers.ChoiceField(
        required=True, choices=RelationType.UI_CHOICES, source='type'
    )
    gender = serializers.ChoiceField(
        choices=Gender.UI_CHOICES, required=True, source="slave.gender"
    )
    first_name = serializers.CharField(required=True, max_length=250, source="slave.first_name")
    last_name = serializers.CharField(required=True, max_length=251, source="slave.last_name")
    patronymic = serializers.CharField(required=True, max_length=252, source="slave.patronymic")
    birth_date = serializers.DateField(
        required=True, source="slave.birth_date", validators=[validate_birth_date]
    )
    full_name = serializers.CharField(read_only=True, max_length=501, source="slave.full_name")

    class Meta:
        fields = (
            "relation_id",
            "patient_id",
            "profile_id",
            "relation_id",
            "relation_type",
            "full_name",
            "last_name",
            "first_name",
            "patronymic",
            "gender",
            "birth_date",
        )

    def validate(self, attrs):
        if not attrs:
            raise DRFValidationError("No data passed")
        return attrs
