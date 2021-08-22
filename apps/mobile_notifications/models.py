from django.db import models
from django.db.models.fields.json import JSONField
from django.utils.translation import ugettext_lazy as _
from push_notifications.models import Device, GCMDevice, APNSDevice

from apps.core.models import TimeStampIndexedModel
from apps.profiles.models import User


class PushLog(TimeStampIndexedModel):
    data = JSONField(verbose_name=_('data'), default=dict, blank=True, null=True)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT)
    event_name = models.CharField(max_length=500, null=True, blank=True)
    appointment_id = models.BigIntegerField(null=True, blank=True)
