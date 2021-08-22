
import base64
from binascii import hexlify
from io import BytesIO
import os.path

from django.utils.translation import ugettext_lazy as _, ugettext as __
from django.db import models
from django.db.models import F
from django.core.files import File
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.utils import timezone

from PIL import Image

from model_utils.models import TimeStampedModel


class ConcatField(F):
    ADD = '||'


class Fixture(models.Model):
    name = models.CharField(max_length=255)
    applied = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "fixture_migrations"
