import re
from datetime import timedelta
from typing import Optional

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core import validators
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.core.validators import validate_email
from django.db import models, IntegrityError
from django.db.models.fields.json import JSONField
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.functional import cached_property
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import ValidationError

from apps.core import utils
from apps.core.models import TimeStampIndexedModel
from apps.core.utils import validate_image_max_size
from apps.profiles import managers
from apps.profiles.constants import ProfileType, ContactType, Gender, ProfileGroupType, RelationType
from apps.profiles.managers import ProfileQuerySet
from apps.profiles.utils import make_full_name
from apps.profiles.validators import phone_validator


class ProfileConstantMixin:
    def _get_type_obj(self):
        obj = self if isinstance(self, Profile) else self.profile
        return obj


class ProfileTypeMixin(ProfileType, ProfileConstantMixin):
    @property
    def is_system(self):
        obj = self._get_type_obj()
        if obj:
            return obj.type == self.SYSTEM

    @property
    def is_doctor(self):
        obj = self._get_type_obj()
        if obj:
            return obj.type == self.DOCTOR

    @property
    def is_patient(self):
        obj = self._get_type_obj()
        if obj:
            return obj.type == self.PATIENT


class GenderMixin(Gender, ProfileConstantMixin):
    @property
    def is_gender_male(self):
        return self._get_type_obj().gender == self.MAN

    @property
    def is_gender_female(self):
        return self._get_type_obj().gender == self.WOMAN

    @property
    def has_gender(self):
        return self._get_type_obj().gender != self.NOT_SET


class User(ProfileTypeMixin, AbstractBaseUser, PermissionsMixin, TimeStampIndexedModel):
    username = models.CharField(
        _('username'),
        max_length=100,
        unique=True,
        help_text=_(
            'Required. 30 characters or fewer. Letters, numbers and ' '@/./+/-/_ characters'
        ),
        validators=[
            validators.RegexValidator(
                re.compile('^[\w.@+-]+$'), _('Enter a valid username.'), 'invalid'
            )
        ],
    )
    name = models.CharField(_('имя'), max_length=100, blank=True, null=True, db_index=True)
    # _email = EMAILField(_('электронная почта'), blank=True, null=True)
    # _phone = models.CharField(_('телефон'), max_length=15, blank=True, null=True)
    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_('Designates whether the user can log into this admin site.'),
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_(
            'Designates whether this user should be treated as '
            'active. Unselect this instead of deleting accounts.'
        ),
    )
    date_joined = models.DateTimeField(_('дата начала регистрации'), default=timezone.now)
    last_visited = models.DateTimeField(_('последнее посещение'), null=True, blank=True)

    # Registration-related fields
    objects = managers.ClinicUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['name']
    REQUIRED_CONTACT_TYPES = [ContactType.PHONE]

    _profile = None

    class Meta:
        verbose_name = _('пользователь')
        verbose_name_plural = _('пользователи')
        swappable = 'AUTH_USER_MODEL'

    def __init__(self, *args, **kwargs):
        self.save_as_type = kwargs.pop('type', None)
        super(User, self).__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        created = not self.pk
        if not created:
            # Need to get the password here before the instance is saved
            previous_password = User.objects.get(pk=self.pk).password
            password_changed = previous_password != self.password

        super(User, self).save(*args, **kwargs)
        if created:
            # Create a new token for DRF token authentication
            self.get_drf_token()

    @property
    def profile(self):
        """Temporary solution until we implement multiple profiles logic"""
        if not self._profile:
            try:
                self._profile = self.profile_set.all()[0]
            except (IndexError, ValueError):
                return None
        return self._profile

    @profile.setter
    def profile(self, profile):
        """Temporary solution until we implement multiple profiles logic"""
        profile.user = self

    def set_password(self, password, reset_token=True):
        super(User, self).set_password(password)
        # Don't bother with token for an unsaved instance,
        # it will be created on `save()`
        if reset_token and self.pk:
            self.recreate_token()

    def get_drf_token(self):
        token, _ = Token.objects.get_or_create(user=self)
        return token

    def recreate_token(self):
        Token.objects.filter(user=self).delete()
        # manually update current instance
        self.auth_token = self.get_drf_token()

    def get_full_name(self):
        if self.profile:
            return self.profile.full_name

    @property
    def email(self):
        return self.contacts.email

    @email.setter
    def email(self, value):
        raise TypeError('Use user.contacts methods to add email')

    @property
    def phone(self) -> str:
        return self.contacts.phone

    @phone.setter
    def phone(self, value):
        raise TypeError('Use user.contacts methods to add phone')

    @property
    def ordered_contacts(self):
        return self.contacts.all().order_by('-is_primary', 'id')

    @property
    def full_name(self):
        return self.get_full_name()

    def set_username(self):
        """
        Sets the final username for the user at the end of registration
        """
        if not self.has_primary_contacts():
            raise ValidationError('У пользователя нет достаточного набора подтвержденных контактов')
        self.username = self.contacts.email or self.contacts.phone

    def has_primary_contacts(self):
        """
        Check if our user has a required set of primary contacts present, active and confirmed
        """
        required_count = 1
        return (
            self.contacts.filter(
                type__in=self.REQUIRED_CONTACT_TYPES, is_primary=True, is_confirmed=True
            ).count()
            >= required_count
        )

    def get_primary_phone_verification_code(self):
        return self.contacts.get_primary_verification_code(Contact.PHONE)

    def get_primary_email_verification_code(self):
        return self.contacts.get_primary_verification_code(Contact.EMAIL)

    def get_notification_phone(self) -> str:
        primary_phone = self.contacts.phone
        if not primary_phone:
            contact = self.contacts.get_phones(confirmed_only=None).first()
            contact_to = contact.value if contact else ''
        else:
            contact_to = primary_phone
        return contact_to

    def get_notification_email(self) -> str:
        """
        For all users, either get the primary email or any confirmed email.
        For unconfirmed, get a non-confirmed primary email.
        Finally, ignore stale emails.
        """
        contact = None
        try:
            contact = self.contacts.get_primary_email()
        except Contact.DoesNotExist:
            pass

        if not contact:
            contact = self.contacts.get_emails().first()

        if not contact:
            try:
                contact = self.contacts.get_primary_email(confirmed_only=False)
            except Contact.DoesNotExist:
                pass
        return contact.value if contact and not contact.is_stale else ''

    def get_picture_url(self):
        return self.profile.get_picture_url()

    def get_picture_new_url(self):
        return self.profile.get_picture_new_url()

    def get_full_picture_set(self):
        return self.profile.get_full_picture_set()

    def generate_and_get_random_password(self):
        password = User.objects.make_random_password()
        self.set_password(password)
        self.save()
        return password

    def get_login_link_token(self):
        return ''
        from apps.auth.utils import login_token_generator

        return login_token_generator.make_token(self)

    def get_uuid(self) -> str:
        return urlsafe_base64_encode(force_bytes(self.pk))

    def get_admin_url(self):
        if not self.pk:
            return
        return reverse(
            'admin:{}_{}_change'.format(self._meta.app_label, self._meta.model_name), args=[self.pk]
        )

    @property
    def patient(self):
        if not self.profile or not self.is_patient:
            return
        return self.profile.patient


class UserToProfile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    profile = models.ForeignKey('Profile', on_delete=models.DO_NOTHING)

    def save(self, *args, **kwargs):
        if UserToProfile.objects.filter(user=self.user, profile=self.profile).exists():
            raise IntegrityError(
                f'UserToProfile already exists for '
                f'user_id={self.user.pk}, profile_id={self.profile.id}'
            )
        super(UserToProfile, self).save(*args, **kwargs)

    class Meta:
        verbose_name = _('связь профиля с пользователем')
        verbose_name_plural = _('связи профилей с пользователями')


class Profile(TimeStampIndexedModel, GenderMixin, ProfileTypeMixin):
    type = models.PositiveSmallIntegerField(
        _('тип'),
        choices=ProfileTypeMixin.PROFILE_TYPES,
        default=ProfileTypeMixin.PATIENT,
        db_index=True,
    )
    users = models.ManyToManyField(User, through=UserToProfile, verbose_name=_('пользователи'))
    full_name = models.CharField(_('полное имя'), max_length=128, blank=True, db_index=True)
    first_name = models.CharField(_('имя'), max_length=128, blank=True, null=True)
    last_name = models.CharField(_('фамилия'), max_length=128, blank=True, null=True)
    patronymic = models.CharField(_('отчество'), max_length=128, blank=True, null=True)
    is_active = models.BooleanField(_('активен'), default=True, db_index=True)
    birth_date = models.DateField(_('дата рождения'), null=True, blank=True, db_index=True)
    gender = models.CharField(
        _('пол'), max_length=5, choices=Gender.MODEL_CHOICES, default=Gender.NOT_SET, blank=True
    )
    picture_draft = models.ImageField(
        _('фото профиля'),
        upload_to='profile_picture_original/',
        null=True,
        blank=True,
        validators=[validate_image_max_size],
    )
    region_as_text = models.CharField(_('регион текстом'), max_length=256, null=True, blank=True)
    # region = models.ForeignKey(
    #     Region, related_name='profiles', blank=True, null=True, on_delete=models.PROTECT)

    # objects = DefaultModeratedManager()
    objects = ProfileQuerySet.as_manager()

    class Meta:
        verbose_name = _('профиль')
        verbose_name_plural = _('профили')

    def __str__(self):
        if self.full_name:
            result = self.full_name
            return result

        if self.pk:
            try:
                return '{}'.format(self.user.username or _('(профиль)'))
            except AttributeError:
                return _('Профиль #{}').format(self.pk)
        else:
            return 'Профиль'

    _user = None

    @property
    def user(self) -> Optional[User]:
        """
        Temporary solution until we implement multiple users logic
        :rtype: User | None
        """
        if not getattr(self, '_user', None):
            try:
                self._user = self.users.all()[0]
            except (IndexError, ValueError):
                self._user = None

        return self._user

    @user.setter
    def user(self, user: User) -> None:
        """Temporary solution until we implement multiple users logic"""
        assert user.pk, f'Cannot set user before {user.__class__.__name__} is saved'
        assert self.pk, f'Cannot set user before {self.__class__.__name__} is saved'
        UserToProfile.objects.create(user=user, profile=self)

    @cached_property
    def picture(self):
        return None
        return self.picture_set.filter(is_default=True).first()

    def get_picture_url(self):
        return ''
        return self.picture.get_absolute_url() if self.picture else ''

    def get_admin_url(self):
        return reverse(
            f'admin:{self._meta.app_label}_{self._meta.model_name}_change', args=[self.pk]
        )

    def make_full_name(self, first_name=None, patronymic=None, last_name=None):
        full_name = make_full_name(
            last_name=last_name or self.last_name,
            first_name=first_name or self.first_name,
            patronymic=patronymic or self.patronymic,
        )
        return full_name

    @property
    def short_full_name(self):
        first_name = self.first_name and self.first_name.capitalize()[0]
        patronymic = self.patronymic and self.patronymic.capitalize()[0]
        return (
            f"{self.last_name} "
            f"{first_name + '.' if first_name else ''} "
            f"{patronymic + '.' if patronymic else ''}"
        )

    def update_full_name(self):
        """
        Check if any parts of a full name have changed
        and update accordingly. Returns True if an update has occured,
        False if not.
        Does nothing for companies.
        """

        full_name = self.make_full_name()
        if self.full_name != full_name and full_name:
            self.full_name = full_name

    @property
    def is_personal_data_filled(self):
        return bool(self.full_name and self.gender and self.birth_date)

    def clean(self):
        self.update_full_name()
        if not self.full_name:
            raise DjangoValidationError(_("full_name cannot be empty"))

    def save(self, *args, **kwargs):
        self.update_full_name()
        super(Profile, self).save(*args, **kwargs)

    def post_approve(self):
        return  # TODO add post-moderation notifications
        if self.is_patient:
            pass
        self.save()

    def post_reject(self):
        return  # TODO add post-reject notifications
        if self.is_patient:
            reason = self.moderation_noncached_request_reason
            context = {}
            if reason:
                context = {'moderators_comment': 'Комментарий модератора: {}'.format(reason)}


class ProfileToGroup(TimeStampIndexedModel):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    group = models.ForeignKey('ProfileGroup', on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        if ProfileToGroup.objects.filter(profile=self.profile, group=self.group).exists():
            raise IntegrityError(
                f'Profile if {self.profile_id} already exists ' f'for group id={self.group_id}'
            )
        super(ProfileToGroup, self).save(*args, **kwargs)

    class Meta:
        verbose_name = _('связь профиля с группой')
        verbose_name_plural = _('связи профилей с группами')


class ProfileGroup(TimeStampIndexedModel):
    title = models.CharField(_('наименование'), max_length=300, db_index=True)
    type = models.CharField(
        _('тип'),
        max_length=255,
        db_index=True,
        choices=ProfileGroupType.CHOICES,
        null=True,
        blank=True,
    )
    profiles = models.ManyToManyField(
        Profile, related_name='groups', verbose_name=_('профили'), through=ProfileToGroup
    )
    integration_data = JSONField(
        verbose_name=_('Данные об интеграции'), encoder=DjangoJSONEncoder, default=dict, blank=True,
    )

    class Meta:
        verbose_name = _('Группа профилей')
        verbose_name_plural = _('Группы профилей')

    def __str__(self):
        return f"Группа {self.id}: {self.title}"


class Relation(TimeStampIndexedModel):
    master = models.ForeignKey(
        Profile,
        verbose_name=_('основной профиль'),
        on_delete=models.CASCADE,
        related_name='relations',
    )
    slave = models.ForeignKey(
        Profile,
        verbose_name=_('зависимый профиль'),
        on_delete=models.DO_NOTHING,
        related_name='slave_relations',
    )
    type = models.CharField(
        _('кем приходится зависимый профиль основному'),
        max_length=255,
        null=True,
        blank=True,
        choices=RelationType.CHOICES,
    )
    can_update_slave_appointments = models.BooleanField(
        _('может основной видеть/изменять назначения зависимого?'), default=False
    )

    @property
    def same_relation_exists(self) -> bool:
        return Relation.objects.filter(master=self.master, slave=self.slave).exists()

    @property
    def short_str(self):
        return f"Отношение. Основной профиль {self.master_id}, зависимый: {self.slave_id}"

    def __str__(self):
        return self.short_str

    class Meta:
        verbose_name = _('Отношение с другим профилем')
        verbose_name_plural = _('Отношения с другими профилями')
        unique_together = ('master', 'slave')


# class Picture(ModeratedModel, BasePicture):
#     original_file = models.ImageField(_('оригинальный файл'), upload_to='profile_picture_original/')
#     profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
#
#     def __init__(self, *args, **kwargs):
#         super(Picture, self).__init__(*args, **kwargs)
#         self.original_file.upload_to = 'profile_picture_original/'
#         self.cropped_file.upload_to = 'profile_picture_cropped/'
#
#     def get_150x150_url(self):
#         if self.cropped_file:
#             image = get_thumbnail(self.cropped_file, '150x150')
#         else:
#             image = get_thumbnail(self.original_file, '150x150')
#         return image.url
#
#     def post_approve(self):
#         """
#         Mark picture as default after it's been approved, unset is_default flag for all other pictures for this user
#         """
#         self.profile.picture_set.filter(is_default=True).update(is_default=False)
#         self.is_default = True
#         self.save()
#         return  # TODO add post-approve notifications
#
#     def post_reject(self):
#         return  # TODO add post-reject notifications
#
#     def load(self, img, copy_to_crop=False):
#         super(Picture, self).load(img)
#         if copy_to_crop:
#             self.cropped_file = self.original_file
#
#     def block(self):
#         """Move profile's picture file and clear staled cache"""
#
#         def rename(f):
#             old_path = f.path
#             f.name = f.name + '_blocked'
#             self._move_file(old_path, f.path)
#
#         if self.original_file.name:
#             self._remove_cached_file(self.original_file)
#             rename(self.original_file)
#         if self.cropped_file.name:
#             self._remove_cached_file(self.cropped_file)
#             rename(self.cropped_file)
#
#         self.save()
#
#     def unblock(self):
#         """Restore original profile's picture filename and clear staled cache"""
#
#         def rename(f):
#             if f.path.endswith('_blocked'):
#                 old_path = f.path
#                 f.name = f.name.replace('_blocked', '')
#                 self._move_file(old_path, f.path)
#
#         if self.original_file.name:
#             rename(self.original_file)
#         if self.cropped_file.name:
#             self._remove_cached_file(self.cropped_file)
#             rename(self.cropped_file)
#
#         self.save()
#
#     def _move_file(self, old_path, new_path):
#         if os.path.isfile(old_path):
#             os.rename(old_path, new_path)
#
#     def _remove_cached_file(self, picture):
#         import sorl
#         if picture:
#             sorl.thumbnail.delete(picture, delete_file=False)
#
#     class Meta:
#         verbose_name = _('изображение профиля')
#         verbose_name_plural = _('изображения профиля')


class Contact(TimeStampedModel, ContactType):
    type_validators = {ContactType.PHONE: phone_validator, ContactType.EMAIL: validate_email}

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='contacts'
    )
    type = models.CharField(_('тип'), max_length=10, db_index=True, choices=ContactType.CHOICES)
    value = models.CharField(_('значение'), max_length=512, db_index=True)
    is_primary = models.BooleanField(_('основной?'), default=False, db_index=True)
    is_confirmed = models.BooleanField(_('подтвержден?'), default=False, db_index=True)
    is_shown = models.BooleanField(_('показывать?'), default=False, db_index=True)
    is_rejected = models.BooleanField(_('отклонен?'), default=False, db_index=True)
    is_deleted = models.BooleanField(_('удален?'), default=False, db_index=True)
    is_stale = models.BooleanField(
        _('не работает?'),
        default=False,
        db_index=True,
        help_text=_('email удален, телефон не отвечает'),
    )
    contact_name = models.CharField(_('контактное лицо'), max_length=255, blank=True)

    objects = managers.ContactManager()
    default_manager = models.Manager()
    UserOwnsContact = managers.UserOwnsContact

    def __str__(self):
        return '{}[{}]: {}'.format(self.user, self.type, self.value)

    def validate_according_to_type(self):
        if self.type in self.type_validators:
            self.type_validators[self.type](self.value)

    def clean(self):
        self.validate_according_to_type()

        if self.is_primary and self.is_confirmed:
            existing_contacts = Contact.objects.filter(
                user=self.user, type=self.type, is_primary=True, is_confirmed=True
            )
            if self.pk:
                existing_contacts = existing_contacts.exclude(pk=self.pk)
            if existing_contacts.exists():
                raise ValidationError(_('У пользователя уже есть основной контакт такого типа'))

    def save(self, *args, **kwargs):
        if self.is_primary and self.is_confirmed:
            self.user.contacts.unset_primary(type=self.type, exclude_pk=self.pk)

        self.full_clean()
        super(Contact, self).save(*args, **kwargs)

    @property
    def is_type_email(self):
        return self.type == ContactType.EMAIL

    @property
    def is_type_phone(self):
        return self.type == ContactType.PHONE

    def confirm(self):
        self.is_confirmed = True
        self.save()

    class Meta:
        verbose_name = _('контакт')
        verbose_name_plural = _('контакты')
        unique_together = [('user', 'type', 'value')]


class ContactVerification(TimeStampedModel):
    CODE_LENGTH = 4

    contact = models.OneToOneField(Contact, on_delete=models.CASCADE, related_name='verification')
    code = models.CharField(_('код'), max_length=32, db_index=True)

    def save(self, *args, **kwargs):
        if not self.pk and not self.code:
            self.code = self.generate_code()
        super(ContactVerification, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.contact.value}: {self.code}"

    @classmethod
    def generate_code(cls, length=CODE_LENGTH):
        return utils.generate_random_code(length)

    @property
    def is_support_available(self):
        """
        Return a date/time when support request will become available for missing verification code
        """
        return utils.moscow_time() > self.modified + timedelta(
            seconds=settings.REGISTRATION_SUPPORT_TIMEOUT_SECONDS
        )

    class Meta:
        verbose_name = _('код подтверждения')
        verbose_name_plural = _('коды подтверждения')
