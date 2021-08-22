# encoding=utf-8

from __future__ import print_function
from __future__ import unicode_literals

import factory


class ModeratedFactory(factory.django.DjangoModelFactory):
    @classmethod
    def _after_postgeneration(cls, obj, create, results=None):
        """Save again the instance if creating and at least one hook ran."""
        if create and results:
            # Some post-generation hooks ran, and may have modified us.
            obj.save(skip_moderation=True)

    @classmethod
    def _get_manager(cls, model_class):
        return model_class.default_manager
