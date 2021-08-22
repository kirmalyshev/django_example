# encoding=utf-8

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from datetime import datetime

from dateutil.tz import tzlocal
from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation, GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.fields import FieldDoesNotExist
from django.db.transaction import atomic
from django.template.loader import render_to_string
from django.urls import reverse, NoReverseMatch
from django.utils.functional import cached_property
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

from apps.core.db import instance_to_python
from apps.core.models import ReloadableModel, TimeStampIndexedModel
from apps.moderation import signals
from apps.moderation.exceptions import EmptyReasonError
from apps.moderation.managers import ModeratedManager, DefaultModeratedManager, RequestManager
from apps.moderation.moderators import register, BaseModerator


class PreValidationMixin(object):
    def pre_moderation_validation(self, action):
        validators = (
            (
                lambda: action in ('approve', 'reject') and not self.is_pending,
                _('Объект должен быть в статусе на модерации.'),
            ),
            (
                lambda: action == 'approve' and self.is_approved,
                _('Невозможно одобрить объект. Объект уже одобрен.'),
            ),
            (
                lambda: action == 'reject' and self.is_rejected,
                _('Невозможно отклонить объект. Объект уже отклонен.'),
            ),
            (
                lambda: action == 'send_to_moderation' and self.is_pending,
                _('Невозможно отправить объект на модерацию. Объект уже на модерации.'),
            ),
        )

        errors = [error_message for is_invalid, error_message in validators if is_invalid()]
        if errors:
            raise ValidationError(errors)


class ModeratedModel(PreValidationMixin, ReloadableModel):
    """
    A base class for every moderated model
    """

    is_displayed = models.BooleanField(
        _('отображается?'), blank=True, default=False, editable=False, db_index=True
    )
    moderated_timestamp = models.DateTimeField(
        _('дата модерации'), blank=True, null=True, db_index=True
    )
    moderation_requests = GenericRelation('moderation.ModerationRequest')

    objects = ModeratedManager()
    default_manager = DefaultModeratedManager()

    is_moderated = True

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):

        model_class = self.__class__
        set_old_values = True

        # TODO decide issue with deferred fields
        # if self._deferred and kwargs:
        #     # This is needed for objects that were retrieved using
        #     # .only() or .deferred() methods
        #     model_class = self._meta.concrete_model
        #     set_old_values = False
        # else:
        #     model_class = self.__class__
        #     set_old_values = True
        model_path = '.'.join([model_class._meta.app_label, model_class._meta.object_name])
        if model_path not in register.moderators and model_class not in register.moderators:
            raise Exception(_('{} is not registered in moderators').format(self.__class__.__name__))
        super(ModeratedModel, self).__init__(*args, **kwargs)

        if set_old_values:
            self._set_old_values()

    def _set_old_values(self):
        self.old_values = instance_to_python(instance=self)

    @atomic
    def approve(self, *args, **kwargs):
        # actually approve by requests
        obj = self.moderator.approve(*args, **kwargs)
        self.is_displayed = (
            True  # So we don't have to reload object to see the updated else where attribute
        )
        self.clear_cache()

        # reset old_values by continue use instance
        obj._set_old_values()
        obj.clear_cache()

        return obj

    def reject(self, *args, **kwargs):
        # actually reject by requests
        obj = self.moderator.reject(*args, **kwargs)
        # So we don't have to reload object to see the updated elsewhere attribute
        if self.moderator.hide_object:
            self.is_displayed = False
            self.clear_cache()
        obj.clear_cache()
        return obj

    def send_to_moderation(self, *args, **kwargs):
        obj = self.moderator.send_to_moderation(*args, **kwargs)
        # So we don't have to reload object to see the updated elsewhere attribute
        if self.moderator.hide_object:
            self.is_displayed = False
            self.clear_cache()
        obj.clear_cache()
        return obj

    def post_approve(self):
        pass

    def post_reject(self):
        pass

    def post_send_to_moderation(self):
        pass

    @cached_property
    def moderator(self):
        return register.get_moderator(self)

    def get_changes(self, watch_fields=None, exclude_fields=None):
        """
        Retrieve field changes for instance in the following format:
        {'field_name': ['Old value', 'New value']}
        Returns two dicts, one containing requested fields, another containing all fields.
        You can specify either which fields to return in the first dict or which fields to exclude.
        Args:
            watch_fields: a list of fields to watch
            exclude_fields: watch all fields except for these
        """
        if exclude_fields:
            exclude_fields = set(exclude_fields)
        else:
            exclude_fields = set()
        exclude_fields.update(['id', 'created', 'modified'])
        all_fields = (
            (field, field.attname)
            for field in self._meta.fields
            if field.attname not in exclude_fields
        )
        watch_fields = watch_fields or all_fields
        all_changes = {}

        for field, attname in all_fields:
            original_value = self.old_values.get(attname, None)
            new_value = field.to_python(getattr(self, attname))
            # First condition is to avoid sending to moderation in cases
            # where original value == '' and new_value == None
            if (original_value or new_value) and original_value != new_value:
                all_changes[attname] = (original_value, new_value)
        watch_changes = {k: v for k, v in all_changes.items() if k in watch_fields}
        return watch_changes, all_changes

    def save(self, skip_moderation=False, changed_by=None, *args, **kwargs):
        if not skip_moderation:
            self.moderator.pre_save_hook(changed_by=changed_by)
            super(ModeratedModel, self).save(*args, **kwargs)
            self.moderator.post_save_hook()
        else:
            if not self.pk:
                self.display(save=False)
            super(ModeratedModel, self).save(*args, **kwargs)
        self._set_old_values()
        self.clear_cache()

    def clear_cache(self):
        # clear prefetch cache
        self.moderation_requests.all()._result_cache = None

    def hide(self, save=True):
        self.is_displayed = False
        if save:
            self.save(skip_moderation=True)

    def display(self, save=True):
        self.is_displayed = True
        if save:
            self.save(skip_moderation=True)

    def get_unmoderated_value(self, field, fallback=None):
        last_moderation = self.last_moderation_request_cached
        if not last_moderation:
            return
        (_, new_value) = last_moderation.watched_changes.get(field, (None, None))
        return new_value or fallback

    def get_last_moderation_request(self, look_for_field=None, exclude_watched_changes=False):
        """
        Returns last moderation request with condition

        :param str look_for_field: changeable field name
        :param bool exclude_watched_changes:
            if true exclude watchable fields and look for the first moderation request,
            otherwise parameter does not matter
        :rtype: Request | None
        """
        query = self.moderation_requests.all()
        if look_for_field:
            query = query.filter(watched_changes__icontains=look_for_field)
        if exclude_watched_changes:
            query = query.filter(watched_changes={})
        return query.first()

    @property
    def last_moderation_request(self):
        return self.get_last_moderation_request()

    @property
    def last_moderation_request_cached(self):
        if not hasattr(self, '_last_moderation_request_cached'):
            self._last_moderation_request_cached = self.last_moderation_request
        return self._last_moderation_request_cached

    @property
    def moderation_request_status(self):
        if self.last_moderation_request_cached:
            return self.last_moderation_request_cached.get_status_display()
        return ''

    @property
    def moderation_request_status_raw(self):
        if self.last_moderation_request_cached:
            return self.last_moderation_request_cached.status
        return ModerationRequest.STATUS_APPROVED

    @property
    def moderation_request_reason(self):
        if self.last_moderation_request_cached:
            return self.last_moderation_request_cached.reason
        return ''

    @property
    def moderation_noncached_request_reason(self):
        if self.last_moderation_request:
            return self.last_moderation_request.reason
        return ''

    @property
    def is_pending(self):
        if self.last_moderation_request_cached:
            return self.last_moderation_request_cached.is_pending
        return False

    @property
    def is_approved(self):
        if self.last_moderation_request_cached:
            return self.last_moderation_request_cached.is_approved
        return True

    @property
    def is_rejected(self):
        if self.last_moderation_request_cached:
            return self.last_moderation_request_cached.is_rejected
        return False

    @property
    def approval_date(self):
        """
        Returns the date of approval for approved objects, None for objects in all other moderation states
        """
        try:
            mod_request = self.last_moderation_request
            if mod_request.is_approved:
                return mod_request.moderated_timestamp
        except AttributeError:
            pass
        return None

    def get_displayed_field_value(self, field_name, *args):
        """
        Return a deserialized stringified representation of a field value
        (i.e. loaded from Request.watched_changes)
        """
        try:
            field_class, x, direct, x = self._meta.get_field_by_name(field_name)
        except FieldDoesNotExist:
            return args

        if not direct:
            raise Exception('Cannot handle indirect fields ({})'.format(field_class))

        raw_value = args[0] if len(args) else getattr(self, field_name)
        if raw_value is None:
            return _('(пусто)')
        if isinstance(field_class, (models.ForeignKey, models.OneToOneField)):
            try:
                return '{}'.format(field_class.related.parent_model.objects.get(pk=raw_value.pk))
            except AttributeError:
                return '{}'.format(field_class.related.parent_model.objects.get(pk=raw_value))

        return raw_value

    def get_stored_field_value(self, field_name, *args):
        """
        Serialize a field value as suitable for Request.watched_changes
        """
        field_class, _, direct, _ = self._meta.get_field_by_name(field_name)
        if not direct:
            raise Exception('Cannot handle indirect fields ({})'.format(field_class))
        value = args[0] if len(args) else getattr(self, field_name)
        if isinstance(field_class, (models.CharField, models.TextField)) and value is None:
            return ''
        elif value is None:
            return None
        else:
            return value

    def moderation_repr(self):
        """
        A hook for representing an object in moderation admin
        """
        return '{}'.format(self)


class ModerationRequest(PreValidationMixin, TimeStampIndexedModel):
    STATUS_REJECTED = -10
    STATUS_PENDING = 0
    STATUS_APPROVED = 10

    STATUS_CHOICES = (
        (STATUS_PENDING, _('на модерации')),
        (STATUS_REJECTED, _('отклонено')),
        (STATUS_APPROVED, _('одобрено')),
    )

    SECTION_MODERATORS = BaseModerator.SECTION_MODERATORS
    SECTION_SUPPORT = BaseModerator.SECTION_SUPPORT
    SECTION_CHOICES = ((SECTION_MODERATORS, _('модераторы')), (SECTION_SUPPORT, _('техподдержка')))

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField(db_index=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    status = models.SmallIntegerField(
        _('статус'), choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True
    )
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('модератор'),
        blank=True,
        null=True,
        editable=False,
        related_name='moderated_by_set',
        on_delete=models.DO_NOTHING,
    )
    moderated_timestamp = models.DateTimeField(_('дата модерации'), blank=True, null=True)
    reason = models.TextField(_('комментарий модератора'), blank=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('кем изменен'),
        blank=True,
        null=True,
        editable=False,
        related_name='changed_by_set',
        on_delete=models.DO_NOTHING,
    )
    watched_changes = JSONField(_('изменения'), blank=True, default=dict)
    section = models.SmallIntegerField(
        _('зона ответственности'), blank=True, null=True, db_index=True, choices=SECTION_CHOICES
    )

    # index by separate watched_changes request
    index = models.SmallIntegerField(blank=True, null=True, db_index=True, editable=False)

    objects = RequestManager()

    class Meta:
        verbose_name = _('запрос на модерацию')
        verbose_name_plural = _('запросы на модерацию')
        ordering = ('-created',)

    def __init__(self, *args, **kwargs):
        super(ModerationRequest, self).__init__(*args, **kwargs)
        # hack by submit line
        self.is_moderated = True
        self.last_moderation_request = self

    @property
    def is_pending(self):
        return self.status == self.STATUS_PENDING

    @property
    def is_approved(self):
        return self.status == self.STATUS_APPROVED

    @property
    def is_rejected(self):
        return self.status == self.STATUS_REJECTED

    def move_changes(self, obj, changes, preserve=False):
        assert isinstance(changes, dict)
        for field, (incoming_original_value, incoming_new_value) in changes.items():
            if self.index is not None and field not in obj.moderator.watched_fields[self.index]:
                continue

            if not preserve:
                setattr(obj, field, incoming_original_value)

            # in case if request has initial field value - it's set as original value.
            if self.watched_changes.get(field):
                original_value = self.watched_changes.get(field)[0]
            else:
                original_value = incoming_original_value

            if original_value != incoming_new_value:
                self.watched_changes[field] = [
                    obj.get_stored_field_value(field, original_value),
                    obj.get_stored_field_value(field, incoming_new_value),
                ]
            else:
                self.watched_changes.pop(field)

    def copy_changes(self, obj, changes):
        self.move_changes(obj, changes, preserve=True)

    def render_changes(self, obj):
        """
        Copy new field values from watched_changes to a supplied.
        self.watched_changes should contain a dict of changes in the format returned by obj.get_changes()
        """
        update_fields = []
        for field, (_, new_value) in self.watched_changes.items():
            setattr(obj, field, new_value)
            update_fields.append(field)
        obj.save(skip_moderation=True, update_fields=update_fields)

    def display_changes(self):
        changes = {}
        for field, (original_value, new_value) in self.watched_changes.items():
            try:
                model_field = self.content_type.model_class()._meta.get_field(field)
                verbose_name = model_field.verbose_name
            except FieldDoesNotExist:
                verbose_name = field
            changes[verbose_name] = [
                self.content_object.get_displayed_field_value(field, original_value),
                self.content_object.get_displayed_field_value(field, new_value),
            ]
        return render_to_string('moderation/display_changes.html', {'changes': changes})

    display_changes.allow_tags = True
    display_changes.short_description = _('изменения')

    def content_object_display(self):
        if not self.content_object:
            return
        object_repr = self.content_object.moderation_repr()
        try:
            object_url = reverse(
                'admin:{}_{}_change'.format(self.content_type.app_label, self.content_type.model),
                args=[self.object_id],
            )
        except NoReverseMatch:
            if hasattr(self.content_object, 'get_absolute_url'):
                object_url = self.content_object.get_absolute_url()
            elif hasattr(self.content_object, 'get_admin_url'):
                object_url = self.content_object.get_admin_url()
            else:
                object_url = ''

        if object_url:
            return format_html(
                '<a href="{}" target="_blank">{}</a>'.format(object_url, object_repr)
            )
        else:
            return object_repr

    content_object_display.short_description = _('объект')
    content_object_display.allow_tags = True

    def accept_change(self, status, moderated_by=None, reason=''):
        self.moderated_by = moderated_by
        now = datetime.now(tz=tzlocal())
        self.moderated_timestamp = now
        self.status = status
        if reason:
            self.reason = reason
        self.save()
        self.content_object.moderated_timestamp = now
        self.content_object.save(
            skip_moderation=True, update_fields=['moderated_timestamp', 'is_displayed']
        )

    def approve(self, *args, **kwargs):
        self.content_object.display(save=False)
        if self.content_object.moderator.hide_fields:
            self.render_changes(self.content_object)
        self.accept_change(self.STATUS_APPROVED, *args, **kwargs)

        self.content_object.post_approve()
        signals.post_approved.send(
            sender=self.content_object.__class__, instance=self.content_object
        )

        return self.content_object

    def reject(self, *args, **kwargs):
        if (
            self.content_object.moderator.require_reason
            and not self.reason
            and not kwargs.get('reason')
        ):
            raise EmptyReasonError

        if self.content_object.moderator.hide_object:
            self.content_object.hide(save=False)
        self.accept_change(self.STATUS_REJECTED, *args, **kwargs)

        self.content_object.post_reject()
        signals.post_rejected.send(
            sender=self.content_object.__class__, instance=self.content_object
        )

        return self.content_object

    def send_to_moderation(self, *args, **kwargs):
        """
        Re-send object to moderation. Does *NOT* get called during regular moderation workflow
        """
        if self.content_object.moderator.hide_object:
            self.content_object.hide(save=False)
        self.accept_change(self.STATUS_PENDING, *args, **kwargs)
        self.content_object.post_send_to_moderation()
        signals.post_send_to_moderation.send(
            sender=self.content_object.__class__, instance=self.content_object
        )

        return self.content_object
