import factory
from django.contrib.auth.models import Group
from django.db.models.signals import post_save, pre_save
from factory import fuzzy
from factory.django import mute_signals

from apps.profiles.constants import (
    ADMIN_USERNAME,
    ProfileType,
    ADD_PRIMARY_PHONE,
    ADD_PRIMARY_EMAIL,
)
from apps.profiles.models import User, Contact
from apps.tools.fuzzy import FIO_LIST, FNAME_LIST, LNAME_LIST, PATRONYMIC_LIST


@mute_signals(pre_save, post_save)
class UserFactory(factory.django.DjangoModelFactory):
    username = factory.Sequence(lambda n: 'test_user_{}@django_example.com'.format(n))
    name = fuzzy.FuzzyChoice(FIO_LIST)

    class Meta:
        model = User
        django_get_or_create = ('username',)

    @classmethod
    def _adjust_kwargs(cls, **kwargs):
        """Extension point for custom kwargs adjustment."""
        kwargs = super(UserFactory, cls)._adjust_kwargs(**kwargs)
        return kwargs

    @classmethod
    def _create(
        cls, model_class, confirm_email=True, password=None, profile=None, *args, **kwargs,
    ):
        skip = False
        username = kwargs.get('username')
        email = kwargs.pop('email', None)
        add_primary_email = kwargs.pop(ADD_PRIMARY_EMAIL, None)
        add_primary_phone = kwargs.pop(ADD_PRIMARY_PHONE, None)
        if username == ADMIN_USERNAME:
            if User.objects.filter(username=ADMIN_USERNAME).exists():
                # Skip any data change to existing admin user
                skip = True

        user = super(UserFactory, cls)._create(model_class, *args, **kwargs)
        if skip:
            return user

        if password:
            user.set_password(password)
            user.save()

        if profile:
            user.profile = profile
            user.save()

        if user.pk:
            if add_primary_email:
                if not email and username and '@' in username:
                    email = username
                try:
                    user.contacts.add_primary_email(email, is_confirmed=confirm_email)
                except Contact.UserOwnsContact:
                    pass
            if add_primary_phone:
                phone_number = '7139' + str(user.pk).zfill(7)
                try:
                    user.contacts.add_primary_phone(phone_number, is_confirmed=True)
                except Contact.UserOwnsContact:
                    pass
        return user


@mute_signals(pre_save, post_save)
class GroupFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: 'Группа {}'.format(n))

    class Meta:
        model = Group
        django_get_or_create = ('name',)


@factory.django.mute_signals(pre_save, post_save)
class ProfileFactory(factory.django.DjangoModelFactory):
    first_name = fuzzy.FuzzyChoice(FNAME_LIST)
    last_name = fuzzy.FuzzyChoice(LNAME_LIST)
    patronymic = fuzzy.FuzzyChoice(PATRONYMIC_LIST)
    type = fuzzy.FuzzyChoice([ProfileType.PATIENT])

    class Meta:
        model = 'profiles.Profile'


@factory.django.mute_signals(pre_save, post_save)
class DoctorProfileFactory(ProfileFactory):
    type = ProfileType.DOCTOR

    class Meta:
        model = 'profiles.Profile'


@factory.django.mute_signals(pre_save, post_save)
class PatientProfileFactory(ProfileFactory):
    type = ProfileType.PATIENT

    class Meta:
        model = 'profiles.Profile'


@factory.django.mute_signals(pre_save, post_save)
class UserToProfileFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
    profile = factory.SubFactory(ProfileFactory)

    class Meta:
        model = 'profiles.UserToProfile'


# @factory.django.mute_signals(pre_save, post_save)
# class PictureFactory(factory.django.DjangoModelFactory):
#     profile = factory.SubFactory(ProfileFactory)
#
#     class Meta:
#         model = 'profiles.Picture'
