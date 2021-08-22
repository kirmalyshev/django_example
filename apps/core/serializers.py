from typing import Set, Dict

import requests
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import RegexValidator

try:
    from django.utils.encoding import smart_text
except ImportError:
    from django.utils.encoding import smart_unicode as smart_text
from django.utils import timezone
from django.utils.timezone import is_aware
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework.relations import SlugRelatedField
from rest_framework.serializers import ManyRelatedField, PrimaryKeyRelatedField  # noqa
from .utils import parse_multivalue_params


class SimpleRelatedField(PrimaryKeyRelatedField):
    """
    Same as PrimaryKeyRelatedField, but works for normal Serializer instead of ModelSerializer.
    It allows passing serializer.data['field_name'] directly to model constructor argument.
    Also, no pk in string representation of object.
    """

    def label_from_instance(self, obj):
        """
        Return a readable representation for use with eg. select widgets.
        """
        return smart_text(obj)

    def field_to_native(self, obj, field_name):
        return obj.get(field_name, None)


class SimpleSlugRelatedField(SlugRelatedField):
    """
    Same as PrimaryKeyRelatedField, but works for normal Serializer instead of ModelSerializer.
    It allows passing serializer.data['field_name'] directly to model constructor argument.
    Also, no pk in string representation of object.
    """

    def label_from_instance(self, obj):
        """
        Return a readable representation for use with eg. select widgets.
        """
        return smart_text(obj)

    def field_to_native(self, obj, field_name):
        return obj.get(field_name, None)


class FileSerializer(serializers.Serializer):
    file = serializers.FileField(required=True)


class DynamicFieldSerializer(serializers.Serializer):
    """
    Serializer with dynamic field. Default field are Meta.recommended_fields.
    Use HTTP GET params fields/exclude_fields/added_fields for control visible fields.
    """

    def __init__(self, *args, **kwargs):
        assert (
            self.Meta.recommended_fields or self.Meta.dynamic_fields
        ), "recommended_fields and dynamic_fields are empty, don't use DynamicFieldSerializer"

        super(DynamicFieldSerializer, self).__init__(*args, **kwargs)

        existing = set(self.fields.keys())

        def parse_data(param):
            if 'context' in kwargs and 'request' in kwargs['context']:
                parse_param = kwargs['context']['request'].query_params.get(param, None)
                if parse_param:
                    return set(
                        field_name
                        for field_name in parse_param.split(',')
                        if field_name in existing
                    )
            return set()

        fields = parse_data('fields') or set(self.Meta.recommended_fields)
        exclude_fields = parse_data('exclude_fields')
        added_fields = parse_data('added_fields')

        for field_name in existing - fields - added_fields | exclude_fields:
            self.fields.pop(field_name)

    class Meta:
        recommended_fields = ()
        dynamic_fields = ()
        fields = recommended_fields + dynamic_fields


class MultiValueMixin:
    """
    Parse multivalue parameters in http request.
    Absolves from the need to use `parse_multivalue_params` in views.
    """

    multivalue_fields: Set[Dict] = set()

    def __init__(self, instance=None, data=serializers.empty, **kwargs):
        if data is not serializers.empty:
            data = parse_multivalue_params(data.copy(), self.multivalue_fields)
        super(MultiValueMixin, self).__init__(instance, data, **kwargs)


class DateTimeTzAwareField(serializers.DateTimeField):
    def to_representation(self, value):
        if not value:
            return
        if is_aware(value):
            value = timezone.localtime(value)
            return super(DateTimeTzAwareField, self).to_representation(value.replace(microsecond=0))
        value = value.replace(tzinfo=timezone.utc)
        value = timezone.localtime(value)
        return super(DateTimeTzAwareField, self).to_representation(value.replace(microsecond=0))


# class MixinModeratedDateSerializer(serializers.Serializer):
#     """
#     Serializer for moderation object.
#     Inherit this class, add fields to Serializer.Meta.fields:
#         `fields = ('a1', 'a2') + MixinModeratedDateSerializer.Meta.fields`
#     """
#     created = DateTimeTzAwareField(read_only=True)
#     modified = DateTimeTzAwareField(read_only=True)
#     moderated_timestamp = DateTimeTzAwareField(read_only=True)
#     time_since_moderation = serializers.SerializerMethodField()
#     time_since_created = serializers.SerializerMethodField()
#
#     def get_time_since_created(self, obj):
#         value = obj.created.replace(tzinfo=timezone.utc)
#         return patched_timesince(value)
#
#     def get_time_since_moderation(self, obj):
#         if obj.moderated_timestamp:
#             value = obj.moderated_timestamp.replace(tzinfo=timezone.utc)
#             return patched_timesince(value)
#
#     class Meta:
#         read_only_fields = fields = (
#             'created', 'modified', 'moderated_timestamp',
#             'time_since_moderation', 'time_since_created'
#         )


class RecaptchaField(serializers.CharField):
    default_error_messages = {
        'blank': _('No reCaptcha value provided.'),
        'invalid': _('Invalid reCaptcha value.'),
    }
    FAKE_VALUE = 'FAKE'
    hardcoded_field_name = 'g-recaptcha-response'

    def is_recaptcha_enabled(self):
        return False
        return config.RECAPTCHA_ENABLED and settings.RECAPTCHA_ENABLED

    def is_fake_recaptcha_enabled(self):
        return settings.FAKE_RECAPTCHA

    def get_value(self, dictionary):
        return dictionary.get(self.hardcoded_field_name, serializers.empty)

    def run_validation(self, data=serializers.empty):
        if self.is_recaptcha_enabled():
            if data == '' or data == serializers.empty:
                self.fail('blank')
            if self.is_fake_recaptcha_enabled():
                if data != self.FAKE_VALUE:
                    self.fail('invalid')
            else:
                try:
                    response = requests.post(
                        settings.RECAPTCHA_API_URL,
                        {'secret': settings.RECAPTCHA_PRIVATE_KEY, 'response': data},
                    )
                except (requests.ConnectionError, requests.Timeout):
                    pass
                else:
                    if not response.json()['success']:
                        self.fail('invalid')


class StaticValueField(serializers.Field):
    default_error_messages = ()

    def __init__(self, *args, **kwargs):
        assert 'default' in kwargs
        kwargs['allow_null'] = False
        if not 'read_only' in kwargs:
            kwargs['read_only'] = False
        super(StaticValueField, self).__init__(*args, **kwargs)
        self.default_empty_html = kwargs['default']

    def get_attribute(self, *args, **kwargs):
        return self.default

    def to_representation(self, *args, **kwargs):
        return self.default

    def __repr__(self):
        return self.default


class IDListSerialzier(serializers.Serializer):
    id = serializers.ListField(child=serializers.IntegerField(), required=False)


class PaginateSerialzier(serializers.Serializer):
    page = serializers.CharField(required=False)
    page_size = serializers.IntegerField(required=False)


class DynamicSerialzier(serializers.Serializer):
    fields = serializers.CharField(required=False)
    exclude_fields = serializers.CharField(required=False)
    added_fields = serializers.CharField(required=False)


class AlphabetField(serializers.CharField):
    def __init__(self, **kwargs):
        super(AlphabetField, self).__init__(**kwargs)
        validator = RegexValidator(
            regex=r'^[a-zA-Zа-яА-ЯёЁ\- ]+$', message=_('Не должно содержать символы и цифры')
        )
        self.validators.append(validator)


class WritableNestedSerializer(serializers.ModelSerializer):
    """
    The nested serializer represents and transforms to the internal value FK object like a same structure.

    For example:
        class NestedSerializer(WritableNestedSerializer):
            class Meta:
                model = BudgetCategory
                fields = ('id', 'title')

        # to representation
        NestedSerializer(instance=budget_category).data,

        # to internal value
        serializer = NestedSerializer(
            data={'id': budget_category.id, 'title': budget_category.title},
            read_only=False
        )
        serializer.is_valid()
        serializer.validated_data  # budget_category
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('read_only', True)
        kwargs.setdefault('default', {})
        super(WritableNestedSerializer, self).__init__(*args, **kwargs)

    def to_internal_value(self, data):
        pk_field = self.fields['id']
        primitive_value = pk_field.get_value(data)
        validated_value = pk_field.to_internal_value(primitive_value)
        try:
            return self.Meta.model.objects.get(pk=validated_value)
        except ObjectDoesNotExist:
            self.fail('does_not_exist', pk_value=data)
        except (TypeError, ValueError):
            self.fail('incorrect_type', data_type=type(data).__name__)


class IdManyRelatedField(ManyRelatedField):
    """
    ManyRelatedField that appends an suffix to the sub-fields.
    Only works together with IdPrimaryKeyRelatedField and our
    ModelSerializer.
    """

    field_name_suffix = '_id'

    def bind(self, field_name, parent):
        """
        Called when the field is bound to the serializer.
        See IdPrimaryKeyRelatedField for more informations.
        """
        self.source = field_name[: -len(self.field_name_suffix)]
        super(IdManyRelatedField, self).bind(field_name, parent)
