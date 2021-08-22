# coding: utf-8
from apps.notify.fixtures.notifygroup_initial import load as group_load
from apps.notify.fixtures.notificationtype_initial import load as type_load
from apps.notify.fixtures.notificationchannel_initial import load as channels_load
from apps.notify.fixtures.event_initial import load as events_load
from apps.notify.fixtures.mailtemplate_initial import load as mailtemplate_load
from apps.notify.fixtures.notifytemplate_initial import load as template_load


def load_all():
    channels_load()
    group_load()
    type_load()

    events_load()
    mailtemplate_load()
    template_load()
