from typing import Dict

from django.contrib.auth.models import AnonymousUser
from django.db.models import Q
from django.db.transaction import atomic
from django.shortcuts import get_object_or_404
from django.utils.crypto import get_random_string
from django.utils.translation import ugettext as _
from rest_framework.exceptions import ValidationError

from apps.notify import send_event
from apps.notify.constants import EMAIL, SMS
from apps.profiles.constants import ContactType
from apps.profiles.serializers import PhoneSerializer, EmailSerializer
from .models import User, ContactVerification, Contact, Profile


class ContactHandler:
    _contact_validators = {ContactType.EMAIL: EmailSerializer, ContactType.PHONE: PhoneSerializer}

    @staticmethod
    def get_phone_query(phone_value):
        return Q(value=phone_value, type=ContactType.PHONE)

    @classmethod
    def get_phone_contact(cls, phone_value):
        """
        :type phone_value: str
        :rtype: apps.profiles.models.Contact | None
        """
        phone_contacts = Contact.objects.select_related('user').filter(
            cls.get_phone_query(phone_value)
        )
        try:
            contact = phone_contacts.get(
                # is_confirmed=False,
                # # cutoff timestamp: registration and confirmation should be near
                # created__gt=timezone.now() - datetime.timedelta(hours=1)
            )
        except Contact.DoesNotExist as err:
            return
        return contact

    @classmethod
    def resend_code(cls, contact):
        """
        :type cls: apps.profiles.handlers.ContactHandler
        :type contact: apps.profiles.models.Contact
        """
        cls.delete_contact_verification(contact)
        cls.add_contact_verification(contact)
        cls.send_verification_code(contact)

    @staticmethod
    def delete_contact_verification(contact):
        """ :type contact: apps.profiles.models.Contact"""
        try:
            contact.verification.delete()
        except ContactVerification.DoesNotExist:
            pass

    @staticmethod
    def add_contact_verification(contact):
        """ :type contact: apps.profiles.models.Contact"""
        ContactVerification.objects.get_or_create(contact=contact)

    @staticmethod
    def send_verification_code(contact, change_primary=False, **kwargs):
        """ :type contact: apps.profiles.models.Contact """
        assert contact.user, 'to send verification code, contact must have user'
        assert contact.verification, 'to send verification code, contact must have verification'
        assert (
            contact.verification.code
        ), 'to send verification code, contact must have verification.code'

        event_params = {}
        if contact.type == contact.EMAIL:
            event_params['channel'] = EMAIL
            event_params['email_value'] = contact.value
            event_name = 'contacts_add_email'
            event_params['context'] = {'email_confirmation_code': contact.verification.code}
            if change_primary:
                event_name = 'email_change_verification_code'

            send_event(event_name, user=contact.user, **event_params)  # TODO to celery or async
        elif contact.type == contact.PHONE:
            event_params['channel'] = SMS
            event_params['phone_value'] = contact.value
            event_name = 'contacts_add_phone'
            event_params['context'] = {'sms_confirmation_code': contact.verification.code}
            print(f'{event_params=}')
            send_event(event_name, user=contact.user, **event_params)  # TODO to celery or async

    @classmethod
    def validate_contact(cls, contact_type, value):
        validator = cls._contact_validators.get(contact_type)
        if validator:
            validator(data={contact_type: value}).is_valid(raise_exception=True)


class UserHandler(object):
    user = None
    just_created = False

    def __init__(self, user):
        assert not isinstance(user, AnonymousUser), 'Cannot handle anonymous users'
        assert user is not None, 'Cannot initialize without user'
        self.user = user

    @classmethod
    def create(cls, profile_type: int, contacts: Dict):
        """
        Create a new User instance with supplied type and contacts.
        User is marked as unregistered, contacts are added as primary but not confirmed.
        """
        email = contacts.get('email')
        phone = contacts.get('phone')
        assert email or phone, 'At least a phone or email should be present in contacts'
        random_username = '_{}_{}'.format(get_random_string(length=6), email or phone)
        user = User.objects.create(username=random_username, type=profile_type)
        if not user.profile:
            user.profile = Profile.objects.create(type=profile_type)

        handler = cls(user)
        handler.just_created = True
        for contact, value in contacts.items():
            if value:
                handler.add_contact(contact, value, is_primary=True)
        return handler

    def set_bunch_of_attributes(self, **attributes):
        """
        Set a bunch of attributes on user in one pass.
        Accepts attributes as kwargs.
        """
        for attribute, value in attributes.items():
            setattr(self.user, attribute, value)
        if attributes:
            self.user.save(update_fields=attributes.keys())

    def _post_add_contact_hook(self, contact, send_notify=False, **contact_kwargs):
        ContactHandler.add_contact_verification(contact)
        if send_notify:
            ContactHandler.send_verification_code(contact, **contact_kwargs)

    def _post_confirm_contact_hook(self, contact):
        ContactHandler.delete_contact_verification(contact)

        # Do some housekeeping for fresh users that are just confirming their first primary contacts
        # that enable them to proceed to the next step
        if self.user.has_primary_contacts():
            self.user.set_username()
            self.user.save()

    def add_contact(self, contact_type, value, send_notify=False, **kwargs):
        """
        Use this whenever you need to add contacts from external API
        """
        kwargs.setdefault('is_primary', False)
        kwargs.setdefault('change_primary', False)
        change_primary = kwargs.get('change_primary')

        ContactHandler.validate_contact(contact_type, value)

        if change_primary or kwargs['is_primary']:
            send_notify = True

        if contact_type == Contact.PHONE:
            try:
                self.user.contacts.get_primary_phone(confirmed_only=False)
            except Contact.DoesNotExist:
                kwargs['change_primary'] = True
            except Contact.MultipleObjectsReturned:
                kwargs['change_primary'] = False

        elif contact_type == Contact.EMAIL:
            try:
                contact = self.user.contacts.get_primary_email(confirmed_only=False)
            except Contact.DoesNotExist:
                pass

        contact = self.user.contacts.add_contact(value=value, type=contact_type, **kwargs)
        self._post_add_contact_hook(contact, send_notify=send_notify, **kwargs)
        return contact

    def add_email(self, *args, **kwargs):
        """
        shortcut add contact with type email
        """
        return self.add_contact(ContactType.EMAIL, *args, **kwargs)

    def add_phone(self, *args, **kwargs):
        """
        shortcut add contact with type phone
        """
        return self.add_contact(ContactType.PHONE, *args, **kwargs)

    def confirm_contact(self, type, value, code=None, replace_primary=True):
        contact = get_object_or_404(self.user.contacts, type=type, value=value)

        try:
            if code is not None and contact.verification.code != code:
                raise ValidationError(_('Неверный код верификации контакта'))
        except ContactVerification.DoesNotExist:
            raise ValidationError(_('Данный код уже использован'))

        if replace_primary:
            # TODO
            #  Before a primary contact can be replaced with a new one,
            #  `resend_codes()` should be called to re-confirm that the user
            #  still has access to it.

            existing_primary = self.user.contacts.filter(type=type, is_primary=True)
            existing_primary.update(is_primary=False)
            contact.is_primary = True
            contact.confirm()
            try:
                self.user.set_username()
            except ValidationError:
                pass
            else:
                self.user.save()
        else:
            contact.confirm()

        self._post_confirm_contact_hook(contact)

        return contact

    def confirm_primary_contact(self, type, value, code=None):
        return self.confirm_contact(type, value, code, replace_primary=True)

    @atomic
    def delete_contact(self, type, value):
        phone = None
        try:
            if type == Contact.PHONE:
                phone = self.user.contacts.get_phones().get(value=value)
        except Contact.DoesNotExist:
            pass

        self.user.contacts.delete_contact(type=type, value=value)

    def delete_email(self, value):
        self.delete_contact(Contact.EMAIL, value)

    def delete_phone(self, value):
        self.delete_contact(Contact.PHONE, value)


class ProfilePermissions(object):
    @classmethod
    def validate(cls, request, user=None):
        user = user or request.user
        if user.is_anonymous:
            return

        # cls._validate_blocks(request, user)
        # cls._validate_registratrion(request, user)

    @classmethod
    def _validate_blocks(cls, request, user):
        return  # TODO add blocks app, to configure patient blocks

    @classmethod
    def _validate_registratrion(cls, request, user):
        return True
