from datetime import date

from dateutil.utils import today
from django.conf import settings
from django.contrib import auth
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.utils.translation import ugettext as _
from rest_auth.serializers import UserDetailsSerializer
from rest_framework import serializers
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.core.serializers import WritableNestedSerializer
from ..core.validators import (
    validate_phone__if_value_contains_only_digits,
    validate_phone__if_russian_country_code,
)
from apps.profiles.constants import Gender
from apps.sms.models import PhoneCode
from .models import Contact, ContactVerification, Profile

UserModel = get_user_model()


class SimpleContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ('id', 'type', 'value')


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = (
            'id',
            'type',
            'value',
            'contact_name',
            'is_primary',
            'is_confirmed',
            'is_rejected',
        )
        read_only_fields = ('is_confirmed', 'id')


class ContactOptionsSerializer(serializers.ModelSerializer):
    contact_name = serializers.CharField(max_length=255, allow_blank=True, required=False)
    is_show = serializers.BooleanField(required=False)

    class Meta:
        model = Contact
        fields = ['contact_name', 'is_show']


class PictureSerializer(serializers.ModelSerializer):
    file = serializers.CharField(source='get_absolute_url')

    class Meta:
        model = 'profiles.Picture'
        fields = ('file', 'is_default', 'created')
        read_only_fields = ('is_default', 'created')


class ProfileSerializer(serializers.ModelSerializer):
    picture = serializers.ImageField(source='picture_draft', required=False)
    gender = serializers.ChoiceField(choices=Gender.UI_CHOICES, required=False)

    class Meta:
        model = Profile
        fields = (
            'id',
            'full_name',
            'first_name',
            'last_name',
            'patronymic',
            'picture',
            'gender',
            'birth_date',
            'is_active',
            'is_personal_data_filled',
            'picture',
            'gender',
            'region_as_text',
        )
        read_only_fields = (
            'full_name',
            'is_active',
            'is_personal_data_filled',
        )


class GetUpdateProfileSerializer(ProfileSerializer):
    class Meta(ProfileSerializer.Meta):
        fields = (
            'id',
            'full_name',
            'first_name',
            'last_name',
            'patronymic',
            'picture',
            'gender',
            'birth_date',
            'is_active',
            'is_personal_data_filled',
            'picture',
            'gender',
            'region_as_text',
        )
        read_only_fields = (
            'id',
            'is_active',
            'full_name',
            'is_personal_data_filled',
        )

    def validate_birth_date(self, value: date):
        if value > today().date():
            raise DRFValidationError(_("Дата рождения не может быть в будущем"))
        return value


class SupportTimerSerializer(serializers.ModelSerializer):
    """
    For support form on step 15
    """

    timestamp = serializers.DateTimeField(source='check_support_timer', format='iso-8601')

    class Meta:
        model = ContactVerification
        fields = ('timestamp',)


class VerificationCodeSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=4)
    # mobile app uses before order creation
    complete_registration = serializers.BooleanField(required=False)


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    password_1 = serializers.CharField(min_length=settings.MIN_PASSWORD_LENGTH)
    password_2 = serializers.CharField(min_length=settings.MIN_PASSWORD_LENGTH)

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(PasswordChangeSerializer, self).__init__(*args, **kwargs)

    def validate(self, attrs):
        auth_test = auth.authenticate(
            username=self.user.username, password=attrs.get('old_password')
        )
        if not auth_test:
            raise DRFValidationError(_('Неверный старый пароль'))
        if attrs.get('password_1') != attrs.get('password_2'):
            raise DRFValidationError(_('Пароли не совпадают'))
        return attrs


class ReplacePrimarySerializer(serializers.Serializer):
    replace_primary = serializers.IntegerField()
    replace_primary_delayed = serializers.IntegerField()


class LookupUserSerializer(serializers.ModelSerializer):
    type = serializers.IntegerField(source='profile.type')
    type_display = serializers.CharField(source='profile.get_type_display')

    class Meta:
        model = UserModel
        fields = ('id', 'name', 'type', 'type_display')


class ClinicUserDetailsSerializer(UserDetailsSerializer):
    class Meta:
        model = UserModel
        fields = ('pk', 'username', 'name', 'is_active')
        read_only_fields = ('is_active',)


class NestedContactSerializer(WritableNestedSerializer):
    class Meta:
        model = Contact
        fields = ('id', 'value')


class PhoneField(serializers.CharField):
    def __init__(self, **kwargs):
        super(PhoneField, self).__init__(**kwargs)
        self.min_length = 6
        self.max_length = 15
        self.required = kwargs.get('required', True)
        self.validators.extend(
            [
                validate_phone__if_value_contains_only_digits,
                validate_phone__if_russian_country_code,
            ]
        )


class PhoneSerializer(serializers.Serializer):
    """Simple phone serializer for validation purposes."""

    phone = PhoneField()
    code = serializers.CharField(min_length=4, max_length=6, required=False, allow_blank=True)

    def __init__(self, user=None, allow_wired=False, *args, **kwargs):
        self.user = user
        self.allow_wired = allow_wired
        self.is_wired = False
        super(PhoneSerializer, self).__init__(*args, **kwargs)

    def validate_phone(self, value):
        try:
            phone_code = PhoneCode.objects.get(code=value[1:4])
        except PhoneCode.DoesNotExist:
            raise DRFValidationError(_('Неверный телефонный код'))

        if phone_code.is_wired and not self.allow_wired:
            raise DRFValidationError(_('Нельзя вводить стационарный телефон'))

        self.is_wired = phone_code.is_wired
        return value


class EmailSerializer(serializers.Serializer):
    """Simple email serializer for validation purposes."""

    email = serializers.EmailField(required=True)
    email_validate = serializers.BooleanField(default=False)

    def validate_email(self, value):
        return value.strip().lower()


class SendFeedbackEmailSerializer(EmailSerializer):
    full_name = serializers.CharField()
    message = serializers.CharField()

    def save(self, **kwargs):
        assert hasattr(self, '_errors') and not self.errors

        validated_data = dict(list(self.validated_data.items()) + list(kwargs.items()))

        send_mail(
            'Сообщение от {}'.format(validated_data['full_name']),
            validated_data['message'],
            validated_data['email'],
            [settings.FEEDBACK_RECEIVER],
        )
