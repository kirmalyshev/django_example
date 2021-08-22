from datetime import timedelta, datetime

from PIL import ExifTags, Image
from celery.task import PeriodicTask, Task
from celery.task import task
from django.conf import settings
from django.utils import timezone
from sentry_sdk import capture_message as sentry_capture_message

from apps.logging.utils import RecordLog
from apps.tools.redis_storage import SimpleRedisStorage


def get_rotation_code(img):
    """
    Returns rotation code which say how much photo is rotated.
    Returns None if photo does not have exif tag information.
    Raises Exception if cannot get Orientation number from python
    image library.
    """
    if not hasattr(img, '_getexif') or img._getexif() is None:
        return None

    for code, name in ExifTags.TAGS.iteritems():
        if name == 'Orientation':
            orientation_code = code
            break
    else:
        RecordLog('sentry.debug').warn('Cannot get orientation code from library.')

    return img._getexif().get(orientation_code, None)


def rotate_image(img, rotation_code):
    """
    Returns rotated image file.

    img: PIL.Image file.
    rotation_code: is rotation code retrieved from get_rotation_code.
    """
    if rotation_code in (1, 2):
        pass
    elif rotation_code in (3, 4):
        img = img.transpose(Image.ROTATE_180)
    elif rotation_code in (5, 6):
        img = img.transpose(Image.ROTATE_270)
    elif rotation_code in (7, 8):
        img = img.transpose(Image.ROTATE_90)
    else:
        RecordLog('sentry.debug').warn('{} is unrecognized rotation code.'.format(rotation_code))

    if rotation_code in (2, 4, 5, 7):
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
    return img


@task
def resize_image(path, image_type):
    try:
        img = Image.open(path)
        img.thumbnail(settings.MAX_IMAGE_ORIGINAL_SIZE)

        rotation_code = get_rotation_code(img)
        if rotation_code is not None:
            img = rotate_image(img, rotation_code)

        img.save(path, image_type.upper())
    except IOError:
        RecordLog('sentry.debug').warn('Cannot process image ({}): {}'.format(image_type, path))


class OneAtATimeMixin(object):
    """
    An abstract tasks with the ability to detect if it has already been queued.
    """

    _connection = None
    abstract = True

    @property
    def redis_connection(self):
        if not self._connection:
            self._connection = SimpleRedisStorage(
                connection_data=settings.TEMPORARY_DATA_CONNECTION, key_prefix=':lock.task'
            )

        return self._connection

    @property
    def lock_name(self):
        return self.__name__

    def pre_start(self):
        """ Extension point """
        pass

    def start(self):
        """ Main logic expected here """
        raise NotImplementedError

    def post_start(self):
        """ Extension point """
        pass

    def _acquire_lock(self):
        return not self.redis_connection.get(self.lock_name) and self.redis_connection.set(
            self.lock_name, 'true', settings.CELERYD_TASK_SOFT_TIME_LIMIT
        )

    def _release_lock(self):
        return self.redis_connection.delete(self.lock_name)

    def run(self):
        # use lock, because celery queue maybe is full and several task run parallel
        if self._acquire_lock():
            try:
                self.pre_start()
                self.start()
                self.post_start()
            finally:
                self._release_lock()
        else:
            err_msg = f"Feed {self.lock_name} is already being imported by another worker"
            sentry_capture_message(err_msg)


class OneAtATimeTask(OneAtATimeMixin, PeriodicTask):
    # run_every = None
    abstract = True


class OneAtATimeSingleTask(OneAtATimeMixin, Task):
    abstract = True


class LastLaunchTimeBaseTask(OneAtATimeTask):
    launch_minutes_delta = 10
    # run_every = crontab(minute='*/10')
    # queue = 'normal'
    last_launch_key = None
    current_launch_time = None
    ignore_result = False
    abstract = True

    def __init__(self):
        if not self.last_launch_key:
            raise ValueError(f"{self.__class__} must define attribute 'last_launch_key'")
        super(LastLaunchTimeBaseTask, self).__init__()

    @property
    def last_launch_time(self):
        if not self.current_launch_time:
            raise ValueError(f"{self.__class__} instance must have attribute 'current_launch_time'")
        stored_value = self.redis_connection.get(self.last_launch_key)

        if stored_value:
            # todo replace to `return dateutil.parser.parse(stored_value)` after new environment release
            return datetime.strptime(stored_value, "%Y-%m-%dT%H:%M:%S+00:00").replace(
                microsecond=0, tzinfo=timezone.utc
            )
        else:
            return self.current_launch_time - timedelta(minutes=self.launch_minutes_delta)

    def pre_start(self):
        self.current_launch_time = timezone.now().replace(microsecond=0)

    def post_start(self):
        self.redis_connection.set(self.last_launch_key, self.current_launch_time.isoformat(), 0)
