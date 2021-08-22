# encoding=utf-8

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import copy
import inspect
from operator import attrgetter

from apps.logging.middleware import log_data
from django.contrib.contenttypes.models import ContentType
from django.db import models

from apps.core.meta import Singleton


class Register(object):
    __metaclass__ = Singleton

    moderators = {}

    def __init__(self):
        pass

    def __call__(self, model, moderator=None):
        moderator = moderator or BaseModerator
        moderator.validate(model)
        self.moderators[model] = moderator

    def get_moderator(self, obj):
        return self.get_moderator_class(obj)(obj)

    def get_moderator_class(self, obj):
        try:
            klass = obj if inspect.isclass(obj) else type(obj)
            model_path = '.'.join([klass._meta.app_label, klass._meta.object_name])
            moderator = self.moderators.get(klass) or self.moderators.get(model_path)
        except AttributeError:
            moderator = None
        if not moderator:
            raise Exception('{.__name__} is not registered with moderation'.format(klass))
        return moderator


register = Register()


class BaseModerator(object):
    STRATEGY_HIDE_FIELDS = 'hide_fields'
    STRATEGY_HIDE_OBJECTS = 'hide_objects'
    STRATEGY_HISTORY_ONLY = 'history_only'

    watched_fields = []
    excluded_fields = []
    default_excluded_fields = ['created', 'modified', 'is_displayed', 'moderated_timestamp']
    strategy = STRATEGY_HIDE_OBJECTS
    owner_field = None

    mod_requests = None
    moderate_staff_changes = False
    ignore_empty = False
    extra_admin_fields = []

    require_reason = False

    section = None
    # Added for convenience when declaring custom moderators
    SECTION_MODERATORS = 1
    SECTION_SUPPORT = 2

    @classmethod
    def validate(cls, model):
        assert cls.strategy in (cls.STRATEGY_HIDE_FIELDS, cls.STRATEGY_HIDE_OBJECTS), cls

        cls.check_normalize_watched_fields(model, cls.watched_fields)

    def __init__(self, obj):
        assert obj

        self.obj = obj
        self.model = type(obj)

        self.register = register
        self.excluded_fields = set(self.excluded_fields + self.default_excluded_fields)

        # forces insert change to Moderation Request
        self.forced_mod_request_insert = False

    @classmethod
    def check_normalize_watched_fields(cls, model, watched_fields):
        if not watched_fields:
            return watched_fields

        need_normalized_watched_fields = []
        for field in model._meta.fields:
            if not field.attname in watched_fields and field.name in watched_fields:
                need_normalized_watched_fields.append(
                    'ERROR watched_field, rename {model}.{name} -> {model}.{attname}'.format(
                        attname=field.attname, name=field.name, model=model.__name__
                    )
                )

        assert not need_normalized_watched_fields, need_normalized_watched_fields

    @property
    def hide_object(self):
        return self.strategy == self.STRATEGY_HIDE_OBJECTS

    @property
    def hide_fields(self):
        return self.strategy == self.STRATEGY_HIDE_FIELDS

    def init_moderation(self, mod_request):
        mod_request.status = mod_request.STATUS_PENDING
        if not mod_request.changed_by:
            mod_request.changed_by = log_data.user
        mod_request.save()
        mod_request.content_object.post_send_to_moderation()

    def create_mod_request(self, **params):
        from .models import ModerationRequest

        return ModerationRequest(content_object=self.obj, section=self.section, **params)

    def request_action(self, action, *args, **kwargs):
        mod_request = None

        for mod_request in self.get_pending_requests():
            getattr(mod_request, action)(*args, **kwargs)

        if mod_request:
            return mod_request.content_object

        return self.model.default_manager.get(pk=self.obj.pk)

    def approve(self, *args, **kwargs):
        return self.request_action('approve', *args, **kwargs)

    def reject(self, *args, **kwargs):
        return self.request_action('reject', *args, **kwargs)

    def send_to_moderation(self, *args, **kwargs):
        return self.request_action('send_to_moderation', *args, **kwargs)

    def get_pending_requests(self, watched_changes=None):
        mod_requests = []

        for mod_request in self.get_requests():
            if mod_request and mod_request.is_pending:
                mod_requests.append(mod_request)

        if not mod_requests:
            mod_requests.append(self.create_mod_request())

        return mod_requests

    def get_request(self, **params):
        from .models import ModerationRequest

        content_type = ContentType.objects.get_for_model(self.obj)
        try:
            return ModerationRequest.objects.filter(
                object_id=self.obj.pk, content_type=content_type, **params
            ).latest('created')
        except ModerationRequest.DoesNotExist:
            return None

    def get_requests(self, watched_changes=None, **params):
        result = self.get_request(**params)
        return [result] if result else []

    def get_watched_changes(self, watched_fields=None):
        watched_fields = watched_fields or self.watched_fields

        watch_all = not watched_fields
        watched_changes, all_changes = self.obj.get_changes(watched_fields, self.excluded_fields)
        if watch_all:
            watched_changes = {
                k: v for k, v in all_changes.items() if k not in self.excluded_fields
            }
        if self.ignore_empty:
            watched_changes = {
                k: (original_value, new_value)
                for k, (original_value, new_value) in watched_changes.items()
                if new_value
            }
        return watched_changes

    def should_moderate_this(self, changed_by=None):
        if changed_by and changed_by.is_staff and not self.moderate_staff_changes:
            return False
        return True

    def need_request(self, watched_changes=None):
        if not self.obj.pk:
            # By new instance, create new Request
            self.mod_requests = [self.create_mod_request()]
        else:
            # get_or_create Request by exists obj
            self.mod_requests = self.get_pending_requests(watched_changes)

    def pre_save_hook(self, changed_by=None):
        """
        Hide new moderated objects or save watched fields content for existing objects,
        create moderation request.

        Gets called from the ModeratedModel during it's save method call in the following order:
        * pre_save_hook
        * save (write to the database)
        * post_save_hook
        """
        from .models import ModerationRequest

        watched_changes = self.get_watched_changes()

        self.forced_mod_request_insert = False

        if self.should_moderate_this(changed_by):

            # By new instance, watched_changes was empty
            if not self.obj.pk:
                # By new instance, create new Request
                self.forced_mod_request_insert = True

                if not self.ignore_empty:
                    # Just hide and init moderation for all new objects by default,
                    # don't check for field changes
                    self.need_request()
                    self.obj.hide(save=False)
                    return

            if watched_changes:
                self.need_request(watched_changes)
                # Default behavior when there are actual changes
                self.forced_mod_request_insert = True
                if self.hide_fields:
                    for mod_request in self.mod_requests:
                        mod_request.move_changes(self.obj, watched_changes)
                elif self.hide_object:
                    for mod_request in self.mod_requests:
                        mod_request.copy_changes(self.obj, watched_changes)
                    self.obj.hide(save=False)

            # no changes or watched_changes is empty
            elif self.ignore_empty:
                # The object either does not contain values in watched fieldss
                # or is an existing instance (and contains no changes)
                watched_fields = (
                    field
                    for field in (
                        self.watched_fields or map(attrgetter('attname'), self.model._meta.fields)
                    )
                    if field not in self.excluded_fields
                )
                if not any(getattr(self.obj, wf) for wf in watched_fields):
                    self.forced_mod_request_insert = False
                    self.obj.display(save=False)

                    existing_requests = self.get_requests(watched_changes)
                    last_request = existing_requests[-1] if existing_requests else None

                    # Create request and approve request if object is_rejected
                    # Replace change and approve request if object is_pending
                    if last_request:
                        if last_request.is_rejected:
                            self.create_mod_request(status=ModerationRequest.STATUS_APPROVED).save()
                        elif last_request.is_pending:
                            last_request.move_changes(self.obj, watched_changes)
                            last_request.status = ModerationRequest.STATUS_APPROVED
                            last_request.save()

                    # Remove other penging requests
                    for existing_request in existing_requests:
                        if existing_request != last_request and existing_request.is_pending:
                            existing_request.delete()

                # The object is new and some watched fields contain values, send to moderation
                elif not self.obj.pk:
                    self.need_request()
        else:
            # If an object does not require moderation, skip it
            if not self.obj.pk:
                self.obj.display(save=False)

    def post_save_hook(self):
        # bind mod_request.content_object after created obj
        if self.forced_mod_request_insert:
            for mod_request in self.mod_requests:
                mod_request.object_id = self.obj.pk
                self.init_moderation(mod_request)


class SeparatedBaseModerator(BaseModerator):
    strategy = BaseModerator.STRATEGY_HIDE_FIELDS

    @classmethod
    def validate(cls, model):
        super(SeparatedBaseModerator, cls).validate(model)
        assert cls.hide_fields and all(isinstance(i, (tuple, list)) for i in cls.watched_fields)
        if cls.ignore_empty:
            raise NotImplementedError(
                'SeparatedBaseModerator with ignore_empty=True is not allowed'
            )

    @classmethod
    def check_normalize_watched_fields(cls, model, watched_fields):
        normalized_watched_fields = []
        for items in watched_fields:
            super(SeparatedBaseModerator, cls).check_normalize_watched_fields(model, items)

    def create_mod_request(self, **params):
        params.setdefault('index', 0)
        return super(SeparatedBaseModerator, self).create_mod_request(**params)

    def _get_needed_index(self, watched_changes):
        if watched_changes is None:
            return range(0, len(self.watched_fields))

        needed_index = set()
        for i, fieldset in enumerate(self.watched_fields):
            if any([watched_field in fieldset for watched_field in watched_changes]):
                needed_index.add(i)
        return needed_index

    def get_requests(self, watched_changes=None, **params):
        result = []
        index_param = copy.copy(params)
        needed_index = self._get_needed_index(watched_changes)

        for i, _ in enumerate(self.watched_fields):
            index_param.update({'index': i})
            mod_request = self.get_request(**index_param)
            if mod_request and mod_request.index in needed_index:
                result.append(mod_request)

        return result

    def get_pending_requests(self, watched_changes=None):
        mod_requests = []
        requests = self.get_requests(watched_changes)
        existing_index = set()
        needed_index = self._get_needed_index(watched_changes)

        if watched_changes is None:
            existing_index = set(range(0, len(self.watched_fields)))

        for mod_request in requests:
            if mod_request and mod_request.is_pending and mod_request.index in needed_index:
                mod_requests.append(mod_request)
                existing_index.add(mod_request.index)

        for i, fieldset in enumerate(self.watched_fields):
            if i not in existing_index and i in needed_index:
                mod_requests.append(self.create_mod_request(index=i))

        if watched_changes is None and not mod_requests:
            mod_requests.append(self.create_mod_request(index=0))

        return mod_requests

    def get_watched_changes(self):
        watched_fields = []
        for i in self.watched_fields:
            watched_fields.extend(list(i))

        return super(SeparatedBaseModerator, self).get_watched_changes(watched_fields)


def check_is_field(model, field_name):
    is_field = True
    try:
        model._meta.get_field(field_name)
    except models.FieldDoesNotExist:
        is_field = False
    return is_field


def make_extra_admin_field(model, field_name):
    """
    Make a callable that returns extra admin field value getter.
    This field becomes visible in moderation request admin
    Use it together with Moderator.extra_admin_fields like this:

    ```
    class OrderModerator(moderators.BaseModerator):
        extra_admin_fields = [
            moderators.make_extra_admin_field(Order, 'get_ip_address_for_admin')
        ]
    ```
    """

    def getter(obj):
        if check_is_field(model, field_name):
            value = getattr(obj.content_object, field_name)
        else:
            value = getattr(obj.content_object, field_name)()
        return value

    if not check_is_field(model, field_name):
        function = getattr(model, field_name)
        getter.allow_tags = getattr(function, 'allow_tags', False)
        if hasattr(function, 'short_description'):
            getter.short_description = getattr(function, 'short_description')
    return getter
