from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.core.serializers import DateTimeTzAwareField
from apps.reviews.constants import GRADE
from apps.reviews.models import Review, ReviewGrade


class ReviewPublicSerializer(serializers.ModelSerializer):
    doctor_full_name = serializers.CharField(source='doctor.short_full_name')
    author_first_name = serializers.CharField(source='author_patient.profile.first_name')
    created = DateTimeTzAwareField()

    class Meta:
        model = Review
        read_only_fields = fields = (
            'id',
            'created',
            GRADE,
            # 'patient_id',
            'doctor_id',
            'doctor_full_name',
            # 'appointment_id',
            'text',
            "author_first_name",
        )


class ReviewPrivateSerializer(ReviewPublicSerializer):
    class Meta(ReviewPublicSerializer.Meta):
        read_only_fields = fields = (
            'id',
            'created',
            GRADE,
            'doctor_id',
            'doctor_full_name',
            'appointment_id',
            'text',
            "author_first_name",
        )


class ReviewForAppointmentSerializer(ReviewPrivateSerializer):
    class Meta(ReviewPrivateSerializer.Meta):
        read_only_fields = fields = (
            'id',
            'created',
            GRADE,
            'doctor_id',
            'doctor_full_name',
            'text',
            "author_first_name",
        )


class ReviewTextCharField(serializers.CharField):
    default_error_messages = {
        'required': _("Напишите, пожалуйста, комментарий."),
        'invalid': _('Not a valid string.'),
        'blank': _('Напишите, пожалуйста, комментарий. Он не может быть пустым.'),
        'max_length': _('Ensure this field has no more than {max_length} characters.'),
        'min_length': _('Ensure this field has at least {min_length} characters.'),
    }


class ReviewGradeField(serializers.IntegerField):
    default_error_messages = {
        'required': _("Укажите, пожалуйста, оценку."),
        'invalid': _('Not a valid string.'),
        'blank': _('Укажите, пожалуйста, оценку.'),
        'max_value': _('Ensure this value is less than or equal to {max_value}.'),
        'min_value': _('Ensure this value is greater than or equal to {min_value}.'),
        'max_string_length': _('String value too large.'),
    }


class CreateAppointmentReviewSerializer(serializers.ModelSerializer):
    appointment_id = serializers.IntegerField(required=True, read_only=False, min_value=1)
    grade = ReviewGradeField(
        required=True, read_only=False, min_value=ReviewGrade.ONE, max_value=ReviewGrade.FIVE
    )
    text = ReviewTextCharField(required=True, read_only=False, max_length=10000,)

    class Meta:
        model = Review
        fields = (
            GRADE,
            'appointment_id',
            'text',
        )


class ReviewListFilterParamsSerializer(serializers.Serializer):
    doctor_id = serializers.IntegerField(required=False, min_value=1)
