import base64
import os
import random
import re
import uuid
from binascii import hexlify
from datetime import tzinfo, timedelta, datetime, time
from distutils.dir_util import create_tree
from functools import partial

from celery.schedules import crontab
from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.paginator import Paginator, EmptyPage, InvalidPage
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from rest_framework.exceptions import ValidationError as DRFValidationError

MONEY_PARAMS = dict(decimal_places=2, max_digits=14)


def generate_uuid() -> str:
    return str(uuid.uuid4())


def make_absolute_url(url) -> str:
    return f'{settings.PREFIX_URL}{url}'


def generate_random_id(length=32):
    return hexlify(os.urandom(int(length / 2)))


def validate_chars(string, allowed_chars):
    """
    Check whether all `string` chars are from `allowed_chars`.
    `allowed_chars` should be a string, e.g. "abcde123".
    """
    for i in string:
        if i not in allowed_chars:
            return False
    return True


def generate_random_code(length=4):
    return str(random.SystemRandom().randint(0, (10 ** length) - 1)).zfill(length)


def create_whole_path(path):
    """ensure the directory structure for trailing file is created"""
    create_tree('/', [path])


class MskTzinfo(tzinfo):
    def utcoffset(self, date_time):
        return timedelta(hours=3)

    def tzname(self, date_time):
        return 'MSK'

    def dst(self, date_time):
        return timedelta(0)


MSK = MskTzinfo()


def moscow_time(date_time=None):
    return date_time.astimezone(MSK) if date_time else datetime.now(tz=MSK)


def validate_base64_image(encoded_data):
    return True
    try:
        img_binary = base64.b64decode(encoded_data)
    except TypeError:
        raise DRFValidationError(_('Wrong Base64 encoded string.'))

    file = SimpleUploadedFile("image.jpg", img_binary)
    serializer = PictureSerializer(data={'img': file})
    serializer.is_valid(raise_exception=True)

    return file


def validate_base64_file(encoded_data, file_type):
    from .serializers import FileSerializer

    try:
        file_binary = base64.b64decode(encoded_data)
    except TypeError:
        raise DRFValidationError(_('Wrong Base64 encoded string.'))

    file = SimpleUploadedFile("file.{}".format(file_type), file_binary)
    serializer = FileSerializer(data={'file': file})
    serializer.is_valid(raise_exception=True)

    return file


class UploadHandler:
    def __init__(self, instance, field_to_save, file_obj):
        self.instance = instance
        self.field_to_save = field_to_save
        self.file_obj = file_obj
        self.path = None

    def get_path(self):
        """Generate full and partial path to save file"""
        random_name = generate_random_id()
        hash_name = HashRing(range(settings.FILE_HASH_ELEMENTS)).get_node(random_name)
        partial = '{}/{}/{}__{}{}'.format(
            self.instance.__class__.__name__,
            hash_name,
            self.instance.id,
            random_name,
            self.get_extension(),
        )
        path = settings.MEDIA_ROOT + '/' + partial
        create_whole_path(path)
        self.path = path
        return path, partial

    def get_extension(self):
        name = self.file_obj.name
        file, extension = os.path.splitext(name)
        extension = extension.lower()
        if not extension or extension == '.jpeg':
            extension = '.jpg'
        return extension

    def check_valid_image(self):
        import imghdr

        image_type = imghdr.what(self.path)
        if image_type:
            return image_type

    def resize_image(self):
        """Applies only for images. Resizes to maximum required size avoiding storing huge original image"""
        image_type = self.check_valid_image()
        if image_type:
            resize_image.delay(self.path, image_type)

    def save_uploaded_file(self, skip_resize=False):
        path, partial_path = self.get_path()
        with open(path, 'wb+') as destination:
            for chunk in self.file_obj.chunks():
                destination.write(chunk)
        setattr(self.instance, self.field_to_save, partial_path)
        self.instance.save()
        if not skip_resize:
            self.resize_image()


def save_base64_image(instance, field_to_save, encoded_data):
    file = validate_base64_image(encoded_data)
    random_name = generate_random_id()
    hash_name = HashRing(range(settings.FILE_HASH_ELEMENTS)).get_node(random_name)
    partial = '{}/{}/{}__{}.jpg'.format(
        instance.__class__.__name__, hash_name, instance.id, random_name
    )
    path = settings.MEDIA_ROOT + '/' + partial
    create_whole_path(path)
    with open(path, 'wb+') as dest:
        for chunk in file.chunks():
            dest.write(chunk)
    setattr(instance, field_to_save, partial)
    instance.save()
    path = settings.MEDIA_ROOT + '/' + partial
    return path


def save_base64_file(model, field_to_save, encoded_data, file_type, data):
    file = validate_base64_file(encoded_data, file_type)

    partial = '{}/{}.{}'.format(model.__name__, generate_random_id(), file_type)
    path = settings.MEDIA_ROOT + '/' + partial

    create_whole_path(path)
    with open(path, 'wb+') as dest:
        for chunk in file.chunks():
            dest.write(chunk)
    data[field_to_save] = partial
    model.objects.create(**data)


def parse_multivalue_params(data, params):
    """
    Extracts list values from data, and updates if value has getlist method
    :param data:  payload data
    :param params: list of multivalue params
    """
    new_data = dict()
    if hasattr(data, 'getlist'):
        for k in data:
            if k not in params:
                new_data[k] = data[k]
        for param in params:
            new_data[param] = data.getlist(param)
        return new_data

    return data


def midnight(date_time=None):
    zero_hour = dict(hour=0, minute=0, second=0, microsecond=0)
    if date_time:
        return date_time.replace(**zero_hour)
    else:
        return datetime.now(tz=MSK).replace(**zero_hour)


def end_of_day(date_time=None):
    last_moment = dict(hour=23, minute=59, second=59, microsecond=999999)
    if date_time:
        return date_time.replace(**last_moment)
    else:
        return datetime.now(tz=MSK).replace(**last_moment)


def today_range(date_time=None):
    if not date_time:
        date_time = datetime.now()
    return [midnight(date_time), end_of_day(date_time)]


def now_in_default_tz() -> datetime:
    return timezone.localtime(timezone.now(), timezone=timezone.get_default_timezone())


def dt_no_seconds(dt: datetime) -> datetime:
    return dt.replace(second=0, microsecond=0, tzinfo=None)


def human_dt(dt: datetime) -> str:
    dt = dt_no_seconds(dt)
    return f'{dt:%d.%m.%Y %H:%M}' if dt else ''


def datetime_tz_formatted(dt: datetime) -> str:
    if not dt:
        return ""
    value = dt_no_seconds(dt)
    value_date = value.date() if value else ""
    if not value_date:
        return ""
    value_date_formatted = f"{value_date:%d.%m.%Y}" if value_date else ""
    return value_date_formatted


crontab_in_default_tz = partial(crontab, nowfun=now_in_default_tz)


def is_now_workday(**kwargs) -> bool:
    now = now_in_default_tz()
    day_start = time(hour=7, minute=50)
    day_end = time(hour=20, minute=0)

    weekday = now.isoweekday()
    if weekday == 6:
        day_end = time(hour=17, minute=0)
    elif weekday == 7:
        day_end = time(hour=15, minute=0)
    now_time = now.time()

    if kwargs.get('print'):
        print(f"{day_start=}, {now=}, {now_time=}, {day_end=}")

    return day_start < now_time < day_end


class PaginationPrepared:
    default_page = 1
    objects_per_page = settings.DEFAULT_PAGE_SIZE
    max_objects_per_page = 50
    page_object = None
    page_exception = None

    def remove_page_data(self, data):
        data.pop('page', None)
        data.pop('page_size', None)
        return data

    def _paginate(self, page, page_size, queryset):
        page = page or self.default_page
        page_size = page_size or self.objects_per_page

        if page_size > self.max_objects_per_page:
            raise DRFValidationError(_('Превышен лимит кол-ва объектов на одну страницу'))
        page_size = min(self.max_objects_per_page, page_size)
        paginator = Paginator(queryset, page_size)
        try:
            self.page_object = paginator.page(page)
        except (EmptyPage, InvalidPage) as page_exception:
            self.page_exception = page_exception
            # obj_lst = paginator.page(paginator.num_pages)
            return []
        queryset = self.page_object.object_list
        return queryset


# TIMESINCE_REPLACEMENTS = {
#     'минуту': 'мин.', 'минуты': 'мин.', 'минут': 'мин.',
#     'часа': 'ч.', 'часов': 'ч.', 'час': 'ч.',
#     'дней': 'д.', 'дня': 'д.', 'день': 'д.',
#     'неделю': 'нед.', 'недель': 'нед.', 'недели': 'нед.',
#     'месяца': 'мес.', 'месяцев': 'мес.', 'месяц': 'мес.',
#     'года': 'г.', 'год': 'г.',
# }
# TIMESINCE_REPLACEMENTS_KEYS = TIMESINCE_REPLACEMENTS.keys()
# TIMESINCE_REPLACEMENTS_KEYS.sort(reverse=True)
# TIMESINCE_PATTERN = re.compile("(%s)" % "|".join(map(re.escape, TIMESINCE_REPLACEMENTS_KEYS)))
#
#
# def patched_timesince(date, strategy='default', short=False):
#     """Special patched timesince filter for different kinds date representation:
#     strategy == 'default' - default django filter behavior
#     strategy == 'literal_today_yesterday' - will return "today"/"yesterday" instead of hours/days and hours
#     strategy == 'literal_yesterday' - will return default django hours for today.
#         "Yesterday" for  yesterday"""
#
#     translation.activate('ru')
#
#     default_res = timesince(date).replace(',', ' ')
#
#     if short:
#         default_res = TIMESINCE_PATTERN.sub(
#             lambda mo: TIMESINCE_REPLACEMENTS[mo.string[mo.start():mo.end()]],
#             default_res
#         )
#     if strategy == 'default':
#         since = default_res
#     else:
#         now = timezone.now()
#         if not date.tzinfo:
#             date = timezone.make_aware(date, timezone.get_default_timezone())
#         days = (now - date).days
#         if days == 0:
#             if strategy == 'literal_today_yesterday':
#                 since = _('сегодня')
#             else:
#                 # Check if it's the same day or not
#                 if date.day == now.day:
#                     since = default_res
#                 else:
#                     since = _('вчера')
#         elif days == 1:
#             since = _('вчера')
#         elif days > 30:
#             since = _('более месяца назад')
#         else:
#             since = default_res
#     translation.deactivate()
#
#     return since


# def cached(seconds=900):
#     """Can be used for a function decoration"""
#     _djcache = get_cache('memcached')
#
#     def do_cache(func):
#         def wrap(*args, **kwargs):
#             key = sha1(
#                 str(func.__module__) + str(func.__name__) + str(args) + str(kwargs)).hexdigest()
#             result = _djcache.get(key)
#             if result is None:
#                 result = func(*args, **kwargs)
#                 _djcache.set(key, result, seconds)
#             return result
#
#         return wrap
#
#     return do_cache


SPLITTER_PATTERN = re.compile(r'[\s/\\,\.\(\)\-\d\'\!?:`"\+]+')


def split_text(text):
    words = text.strip()

    roman_numerals = [
        'I',
        'II',
        'III',
        'IV',
        'V',
        'VI',
        'VII',
        'VIII',
        'IX',
        'X',
        'XX',
        'XXX',
        'XL',
        'L',
        'LX',
        'LXX',
        'LXXX',
        'XC',
        'C',
        'CC',
        'CCC',
        'CD',
        'D',
        'DC',
        'DCC',
        'DCCC',
        'CM',
    ]

    result = set()

    for word in SPLITTER_PATTERN.split(words):
        if word and word not in roman_numerals:
            result.add(word)

    return result


def declension_of_numerals(numeric, variants):
    """
    :numeric: any numeric symbol
    :variants: list of 3 variants
    Example:
    input: declension_of_numerals(1, ['день', 'дня', 'дней'])
    output: 'день'
    """

    if numeric % 100 in (11, 12, 13, 14):
        variant = variants[2]
    elif numeric % 10 == 1:
        variant = variants[0]
    elif numeric % 10 in (2, 3, 4):
        variant = variants[1]
    else:
        variant = variants[2]

    return variant


def get_related_fields(obj, model_class):
    fks = [
        f.name
        for f in obj._meta.fields
        if type(f) == models.fields.related.ForeignKey and f.rel.to == model_class
    ]
    m2ms = [
        f.name
        for f in obj._meta.many_to_many
        if type(f) == models.fields.related.ManyToManyField and f.rel.to == model_class
    ]
    return fks, m2ms


def generate_login_link(url, user):
    """
    Add auto-login token to specified URL.

    Appends pair of params (user id (uidb64) and token) to specified URL to
    allow user to auto-login using generated URL.
    For generated URL validation mechanics see `apps.auth.decorators.auth_by_token`.
    """
    # TODO add params with some url tools
    return '{url}?uidb64={uuid}&token={token}'.format(
        url=url, token=user.get_login_link_token(), uuid=user.get_uuid()
    )


class CompanyInfo:
    """
    Company info, like INN, owner, and something like that
    """

    def __init__(self, timestamp=None):
        self.timestamp = timestamp

    @property
    def timeless_config(self):
        return settings.TIMELESS_COMPANY_INFO

    @property
    def temporary_config(self):
        return settings.TEMPORARY_COMPANY_INFO

    def get(self, key, timestamp=None):
        if key in self.timeless_config:
            return self.timeless_config[key]

        timestamp = timestamp or self.timestamp or timezone.now()
        if not timestamp.tzinfo:
            timestamp = timezone.make_aware(timestamp, timezone.get_default_timezone())

        # find max actual config date with exists config key
        try:
            max_actual_config_date = max(
                date
                for date in self.temporary_config.keys()
                if timestamp >= date and key in self.temporary_config[date]
            )
        except ValueError:
            max_actual_config_date = None

        return self.temporary_config[max_actual_config_date][key]

    def __getitem__(self, key):
        return self.get(key)

    def __getattr__(self, key):
        return self.get(key)


company_info = CompanyInfo()


def validate_image_max_size(image):
    file_size = image.file.size
    limit_mb = 4.5
    if file_size > limit_mb * 1024 * 1024:
        raise DjangoValidationError(_(f"Max size of file is {limit_mb} MB"))
