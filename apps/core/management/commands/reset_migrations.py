# encoding=utf-8

from __future__ import unicode_literals

from click._compat import raw_input
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        response = raw_input(
            "You are about to clear contents of django_migrations table. Are you sure? (yes/No): "
        )
        if response.lower() not in ['y', 'yes']:
            return
        print("Deleting contents of django_migrations table")
        cursor = connection.cursor()
        cursor.execute("TRUNCATE django_migrations")
        print("Done.")
