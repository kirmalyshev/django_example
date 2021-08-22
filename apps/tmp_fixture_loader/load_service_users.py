# coding: utf-8

from apps.profiles.fixtures.users_initial import load as users_load
from apps.profiles.factories import *


def load_all():
    users_load()
