# encoding=utf-8

from __future__ import print_function, unicode_literals

import factory
from factory import fuzzy
from django.db.models.signals import post_save, pre_save


@factory.django.mute_signals(pre_save, post_save)
class MobileCodeFactory(factory.django.DjangoModelFactory):
    code = factory.Sequence(lambda n: '7139{}'.format(n))
    provider = factory.Sequence(lambda n: 'Сотовый оператор {}'.format(n))

    class Meta:
        model = 'sms.PhoneCode'
        django_get_or_create = ('code',)


@factory.django.mute_signals(pre_save, post_save)
class WiredPhoneCodeFactory(factory.django.DjangoModelFactory):
    is_wired = True
    code = fuzzy.FuzzyInteger(100, 999)
    digits_number = 7

    class Meta:
        model = 'sms.PhoneCode'
        django_get_or_create = ('code',)
