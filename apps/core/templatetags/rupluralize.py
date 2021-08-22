# encoding=utf-8

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from django.template import Library
from django.template.defaultfilters import stringfilter

from ..decorators import mute_errors
from ..utils import declension_of_numerals

register = Library()


@mute_errors
@register.filter
@stringfilter
def rupluralize(value, endings):
    """
    Usage:
    25 зака{{ 25|rupluralize:'з,за,зов' }}
    ->
    25 заказов

    3 зака{{ 3|rupluralize:'з,за,зов' }}
    ->
    3 заказа
    """
    endings = endings.split(',')
    return declension_of_numerals(int(value or 0), endings)
