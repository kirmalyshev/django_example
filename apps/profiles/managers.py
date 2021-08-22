from django.contrib.auth.models import UserManager
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned, ValidationError
from django.db import models
from django.db.models.query import QuerySet
from django.utils.translation import ugettext as _


class UserOwnsContact(ValidationError):
    pass


class ClinicUserQuerySet(QuerySet):
    def active(self):
        return self.filter(is_active=True)


class ClinicUserManager(UserManager):
    def get_queryset(self):
        return ClinicUserQuerySet(self.model, using=self._db)


class ContactMixin:
    def _normal_type(self, _type):
        """
        Simple function so we can accept pluralized type names like `phones` or `emails`
        """
        return _type.rstrip('s') if _type not in self.model.TYPES else _type

    def get(self, **kwargs):
        """
        A simple helper for allowing plural contact type forms usage
        """
        if 'type' in kwargs:
            kwargs['type'] = self._normal_type(kwargs['type'])
        return super(ContactMixin, self).get(**kwargs)

    def filter(self, *args, **kwargs):
        """
        A simple helper for allowing plural contact type forms usage
        """
        if 'type' in kwargs:
            kwargs['type'] = self._normal_type(kwargs['type'])
        return super(ContactMixin, self).filter(*args, **kwargs)


class ContactQuerySet(ContactMixin, QuerySet):
    def check_if_stale(self, value):
        return self.filter(value=value, is_stale=True).exists()


class ContactManager(ContactMixin, models.Manager):
    def get_queryset(self):
        return ContactQuerySet(self.model, using=self._db).exclude(is_deleted=True)

    def _reactivate_contact(self, user, value, type):
        try:
            contact = self.model.default_manager.get(
                user=user, value=value.lower(), is_deleted=True, type=type
            )
        except ObjectDoesNotExist:
            pass
        else:
            contact.is_deleted = False
            contact.is_primary = False
            contact.save(update_fields=['is_deleted', 'is_primary'])
            return contact
        return False

    def clean_contact(self, type, value, user=None, change_primary=False):
        """
        Raises a ValidationError whenever another contact of specified type and value is found in the database,
        returns True if no duplicates found.
         Two types of validation: for contacts that cannot be verified (i.e. skype) and verifiable ones.
        """
        clean_value = value.lower()
        lookup_params = dict(type=type, value=clean_value)
        lookup_params_unique = dict(type=type, value=clean_value)
        if user:
            lookup_params_unique.update(dict(user=user))

        existing_contacts = self.model.objects.filter(is_confirmed=True, **lookup_params)
        unique_existing_contacts = self.model.default_manager.filter(**lookup_params_unique)

        if user and existing_contacts.filter(user=user).exists():
            raise UserOwnsContact(_('Пользователь уже имеет данный контакт'))
        elif existing_contacts.exists():
            raise ValidationError(_('Контакт принадлежит другому пользователю'))

        if change_primary and unique_existing_contacts:
            found_contact = unique_existing_contacts[0]
            if not found_contact.is_confirmed:
                # delete unconfirmed contact to allow changing primary contact with the same value
                found_contact.delete()

        return clean_value

    def _check_duplicates(self, type, value, user):
        # Pre-validate attempt to add duplicate:
        clean_value = value.lower()
        lookup_params = dict(type=type, value=clean_value)
        if user:
            lookup_params.update(dict(user=user))
        existing = self.model.default_manager.filter(**lookup_params)

        if existing.exists():
            raise ValidationError(
                _('Контакт, который вы пытаетесь добавить пользователю {} уже используется').format(
                    user
                )
            )

    def _get_related_user(self):
        assert (
            hasattr(self, 'core_filters') and 'user' in self.core_filters
        ), 'Can only be called from RelatedManager'

        return self.core_filters['user']

    def unset_primary(self, type, value=None, exclude_pk=None):
        """
        Remove primary flag from specified (or every) contact of supplied type is set as primary
        """
        # Just a check if we're not getting called on a global queryset
        self._get_related_user()
        type = self._normal_type(type)

        existing_primary = self.filter(type=type, is_primary=True)
        if value:
            existing_primary = existing_primary.filter(value=value)
        if exclude_pk:
            existing_primary = existing_primary.exclude(pk=exclude_pk)

        existing_primary.update(is_primary=False, is_deleted=True, is_confirmed=False)

    def add_contact(self, value, type, change_primary=False, **kwargs):
        """
        Serves to simplify adding contacts to user instances
        """
        # Set the user parameter for create() method explicitly
        # so it cannot be overridden by our method caller
        user = self._get_related_user()
        type = self._normal_type(type)

        # Check contact records for possible duplicates before adding
        clean_value = self.clean_contact(
            type=type, value=value, user=user, change_primary=change_primary
        )

        # If an old contact was found and re-activated, our job here is done, just return the contact
        reactivated_contact = self._reactivate_contact(user=user, value=value, type=type)
        if reactivated_contact:
            return reactivated_contact

        self._check_duplicates(type=type, value=clean_value, user=user)

        # Deactivate a previous primary contact of the same type
        if kwargs.get('is_primary', False) and kwargs.get('is_confirmed', False):
            self.unset_primary(type)
        return self.create(user=user, value=clean_value, type=type, **kwargs)

    def delete_contact(self, value, type, **kwargs):
        type = self._normal_type(type)
        return self.filter(value=value, type=type, **kwargs).update(is_deleted=True)

    def add_phone(self, value, **kwargs):
        return self.add_contact(value, type=self.model.PHONE, **kwargs)

    def add_primary_phone(self, value, **kwargs):
        return self.add_contact(value, type=self.model.PHONE, is_primary=True, **kwargs)

    def get_primary_phone(self, confirmed_only=True):
        return self.get_primary_contact_by_type(self.model.PHONE, confirmed_only)

    def get_phones(self, confirmed_only=True):
        lookup_params = dict(type=self.model.PHONE)
        if confirmed_only:
            lookup_params['is_confirmed'] = True
        return self.filter(**lookup_params)

    def get_all_phones(self, confirmed_only=True):
        lookup_params = dict(type__in=[self.model.PHONE])
        if confirmed_only:
            lookup_params['is_confirmed'] = True
        return self.filter(**lookup_params)

    def add_email(self, value, **kwargs):
        return self.add_contact(value, type=self.model.EMAIL, **kwargs)

    def add_primary_email(self, value, **kwargs):
        return self.add_contact(value, type=self.model.EMAIL, is_primary=True, **kwargs)

    def get_primary_email(self, confirmed_only=True):
        """ :rtype: apps.profiles.models.Contact """
        return self.get_primary_contact_by_type(self.model.EMAIL, confirmed_only)

    def get_emails(self, confirmed_only=True):
        lookup_params = dict(type=self.model.EMAIL)
        if confirmed_only:
            lookup_params['is_confirmed'] = True
        return self.filter(**lookup_params)

    def delete_phone(self, value):
        return self.delete_contact(value, type=self.model.PHONE)

    def delete_email(self, value):
        return self.delete_contact(value, type=self.model.EMAIL)

    def get_primary_contact_by_type(self, contact_type, confirmed_only=True):
        """ :rtype: apps.profiles.models.Contact """
        assert contact_type in self.model.TYPES
        if contact_type == self.model.EMAIL:
            contact = self.get_emails(confirmed_only).get(is_primary=True)
        elif contact_type == self.model.PHONE:
            contact = self.get_phones(confirmed_only).get(is_primary=True)
        return contact

    def is_unique(self, type, value, ignore_user=None):
        if ignore_user is None:
            try:
                ignore_user = self._get_related_user()
            except AssertionError:
                ignore_user = None

        try:
            contact = self.get_queryset().get(type=type, value=value, is_confirmed=True)
        except MultipleObjectsReturned:
            return False
        except ObjectDoesNotExist:
            return True
        else:
            if ignore_user:
                return contact.user == ignore_user
        return True

    @property
    def email(self):
        try:
            contact = self.get_primary_email()
        except self.model.DoesNotExist:
            contact = None
        return contact.value if contact else ''

    @property
    def phone(self) -> str:
        try:
            contact = self.get_primary_phone()
        except self.model.DoesNotExist:
            contact = None
        return contact.value if contact else ''

    def get_primary_verification_code(self, contact_type):
        try:
            contact = self.get_primary_contact_by_type(contact_type, confirmed_only=None)
            code = contact.verification.code
            result = code
        except self.model.DoesNotExist:
            result = None

        return result

    def get_notifyable_types(self, confirmed_only=True):
        params = {'is_primary': True}
        if confirmed_only:
            params['is_confirmed'] = True
        return list(self.filter(**params).distinct('type').values_list('type', flat=True))


class ProfileQuerySet(QuerySet):
    def active(self):
        return self.filter(is_active=True)
