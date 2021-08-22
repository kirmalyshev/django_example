# encoding=utf-8

from __future__ import unicode_literals

import json
import time
import ijson

from optparse import make_option

from django.core.management.base import BaseCommand
from django.db import connection

from rest_framework.utils import encoders

from remontnik_tools.tasks import task_many_serialzer_save


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--serializer', action='store', dest='serializer'),
        make_option(
            '--many', action='store_true', dest='many', default=False, help='Serializer(many=True)'
        ),
        make_option('--query', action='store_true', dest='query', default=False, help='Show query'),
    )

    def handle(self, fixture_labels, *args, **options):
        serializer = options.get('serializer')

        start_time = time.time()
        end_num_queries = len(connection.queries)

        with open(fixture_labels, 'rb') as fixture_file:

            objects = ijson.items(fixture_file, "item")

            queue = []
            for i, obj in enumerate(objects, start=1):
                queue.append(obj)
                if not (i % 50):
                    task_many_serialzer_save.delay(serializer, queue)
                    queue = []

            task_many_serialzer_save.delay(serializer, queue)

        end_time = time.time()
        start_num_queries = len(connection.queries)

        if options.get('query'):
            content = json.dumps(connection.queries, cls=encoders.JSONEncoder, ensure_ascii=True)
            self.stderr.write(content)

        self.stderr.write(
            'OK {0} {1:.3f}s. Queries count: {2}'.format(
                serializer, end_time - start_time, start_num_queries - end_num_queries
            )
        )
