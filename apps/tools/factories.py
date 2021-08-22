# encoding=utf-8

from __future__ import unicode_literals
from __future__ import print_function

from factory.django import DjangoOptions, DjangoModelFactory
from factory.base import OptionDefault


class UpdateOrCreateDjangoOptions(DjangoOptions):
    def _build_default_options(self):
        return super(UpdateOrCreateDjangoOptions, self)._build_default_options() + [
            OptionDefault('django_update_or_create', (), inherit=True)
        ]


class UpdateOrCreateModelFactory(DjangoModelFactory):

    _options_class = UpdateOrCreateDjangoOptions

    class Meta:
        abstract = True

    @classmethod
    def _update_or_create(cls, model_class, *args, **kwargs):
        """Create an instance of the model through objects.update_or_create."""
        manager = cls._get_manager(model_class)

        key_fields = {}
        for field in cls._meta.django_update_or_create:
            key_fields[field] = kwargs.pop(field, None)
        key_fields['defaults'] = kwargs

        obj, _created = manager.update_or_create(*args, **key_fields)
        return obj

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        if cls._meta.django_update_or_create:
            return cls._update_or_create(model_class, *args, **kwargs)

        return super(UpdateOrCreateModelFactory, cls)._create(model_class, *args, **kwargs)
