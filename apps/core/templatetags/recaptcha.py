# encoding=utf-8

from __future__ import print_function
from __future__ import unicode_literals

from django import template
from django.conf import settings

register = template.Library()  # pylint: disable=C0103


@register.simple_tag
def recaptcha_script_tag():
    return '<script src="//www.google.com/recaptcha/api.js" async defer></script>'


@register.simple_tag
def recaptcha_sitekey():
    return settings.RECAPTCHA_PUBLIC_KEY
