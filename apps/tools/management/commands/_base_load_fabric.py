# encoding=utf-8

import os
import sys
import time
from importlib import import_module

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.tools.models import Fixture

TESTING = 'test' in sys.argv


class LoadedFabricStorage(object):
    """
    Record all/runtime loaded fixture
    """

    def __init__(self):
        # all loaded fixture
        self._storage = set(Fixture.objects.all().values_list('name', flat=True))
        # accumulate loaded fixture on runtime
        self._runtime_storage = set()

    def __contains__(self, fixture):
        return fixture in self._storage

    def contains_runtime(self, fixture):
        return fixture in self._runtime_storage

    def add(self, fixture):
        self._runtime_storage.add(fixture)
        self._storage.add(fixture)
        obj, created = Fixture.objects.get_or_create(name=fixture)
        if not created:
            obj.applied = timezone.now()
            obj.save(update_fields=['applied'])


class Command(BaseCommand):
    help = 'Load specific or all fabrics'

    def add_arguments(self, parser):
        # Named (optional) arguments
        parser.add_argument('fabric', type=str, default=None)

        parser.add_argument(
            '--full',
            action='store_true',
            default=False,
            dest='full_load',
            help='Load the specified fabric for all apps.',
        )
        parser.add_argument(
            '--skipinitial', action='store_true', dest='skip_initial', default=False
        )

    def __init__(self, *args, **kwargs):
        self.full = False
        self.skip_initial = False

        super(Command, self).__init__(*args, **kwargs)

    def handle(self, *args, **options):
        # full_load is loading heavy fabric from `full_load` methods if they are exist
        self.full = options.get('full_load', False)
        self.skip_initial = options.get('skip_initial', False)
        fabric = options['fabric']
        self.loaded_fabrics = LoadedFabricStorage()

        if fabric:
            # if specific fabric
            self.load_fabric(fabric)
        else:
            # if nonspecific load
            self.load_all()

    def load_all(self):
        self.find_fabric(self.fixture_dirs())

    def get_app_paths(self):
        return sorted(
            [
                os.path.join(settings.APPS_DIR, name + os.path.sep)
                for name in os.listdir(settings.APPS_DIR)
            ]
        )

    def fixture_dirs(self):
        """
        Return a list of fixture directories.

        The list contains the 'fixtures' subdirectory of each installed
        application, if it exists, the directories in FIXTURE_DIRS, and the
        current directory.

        !!! MODIFIED function from django loaddata command
        """
        dirs = []

        for path in self.get_app_paths():
            d = os.path.join(os.path.dirname(path), 'fixtures')
            if os.path.isdir(d) and ''.join((settings.BASE_DIR, os.path.sep)) in d:
                dirs.append(d)

        dirs = [os.path.abspath(os.path.realpath(d)) for d in dirs]
        return dirs

    def find_fabric(self, dirs):
        for folder in dirs:
            files = sorted(
                [
                    fixture
                    for fixture in os.listdir(folder)
                    if fixture.endswith('.py') and fixture != '__init__.py'
                ]
            )
            path = folder.replace(settings.BASE_DIR, '', 1)
            for fixture in files:
                if fixture.startswith('test_'):
                    continue
                if self.skip_initial and fixture.endswith('initial.py'):
                    continue
                fabric = ''.join((path, os.path.sep, fixture))
                self.load_fabric(fabric)

    def _call_load(self, module, attribute='load'):
        self.stdout.write(f'Loading fixture from {module.__name__}... ', ending='')
        if module.__name__ in self.loaded_fabrics and (
            not self.full or self.loaded_fabrics.contains_runtime(module.__name__)
        ):
            self.stdout.write('SKIPPING, already loaded')
            return

        t1 = time.time()
        getattr(module, attribute)()
        t2 = time.time()
        self.stdout.write('OK, {0:.3f}s'.format(t2 - t1))
        self.loaded_fabrics.add(module.__name__)

    def load_fabric(self, fabric):

        if self.skip_initial and fabric.endswith('initial'):
            return
        if os.path.sep in fabric:
            fabric = fabric.replace(os.path.sep, '.')
            if fabric.endswith('.py'):
                fabric = fabric.replace('.py', '')
            if fabric.startswith('.'):
                fabric = fabric.replace('.', '', 1)
        try:
            module = import_module(fabric)
            loaded = True
        except ImportError as err:
            msg = "An error occured while importing fabric {}".format(fabric)
            err.args = (err.args if err.args else tuple()) + (msg,)
            raise

        # exclude fabrics with for-test mark from standart mode
        if getattr(module, 'FOR_TEST_ONLY', False) and not TESTING:
            loaded = False

        # exclude fabrics with skip-test mark from test mode
        if getattr(module, 'SKIP_FOR_TEST', False) and TESTING:
            loaded = False

            # TODO: Refactor SKIP_FOR_TEST check
            try:
                self._call_load(module, 'test_load')
            except AttributeError:
                pass

        depends_on = getattr(module, 'DEPENDS_ON', [])
        for depend in depends_on:
            self.load_fabric(depend)

        if loaded:
            if not callable(getattr(module, 'load', None)):
                raise CommandError(
                    f"Fixture {module.__name__} rejected: please define `load` method"
                )
            if self.full:
                self._call_load(module)
            else:
                if not getattr(module, 'HEAVY', False):
                    self._call_load(module)
                else:
                    self.stdout.write(f'Skipping {module.__name__} (HEAVY=True)')
