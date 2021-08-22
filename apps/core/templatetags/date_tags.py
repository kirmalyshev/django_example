# encoding=utf-8

from __future__ import unicode_literals

from django.template import Library
from django.utils.timesince import timesince
from iso8601 import iso8601

register = Library()


@register.filter
def parse_date(value):
    try:
        value = iso8601.parse_date(value)
    except iso8601.ParseError:
        return
    return value


@register.filter
def short_timesince(value):
    if value:
        parts = timesince(value).split(', ')
        return parts[0]
    return ''
