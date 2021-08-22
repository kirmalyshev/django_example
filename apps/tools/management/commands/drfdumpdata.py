# encoding=utf-8

from __future__ import unicode_literals

import json
import time

from importlib import import_module

from optparse import make_option

from django.core.management.base import BaseCommand
from django.db import connection

from rest_framework.utils import encoders


def import_from(name):
    attrs = None
    if ':' in name:
        name, attrs = name.split(':')
    module, method = name.rsplit('.', 1)
    method_class = getattr(import_module(module), method)
    if attrs:
        for i in attrs.split('.'):
            method_class = getattr(method_class, i)
    return method_class


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--model', action='store', dest='model'),
        make_option('--serializer', action='store', dest='serializer'),
        make_option(
            '--many', action='store_true', dest='many', default=False, help='Serializer(many=True)'
        ),
        make_option('--query', action='store_true', dest='query', default=False, help='Show query'),
    )

    def get_queryset(self, model_class, serializer_class):
        queryset = model_class.objects.all()
        return queryset

    def handle(self, *args, **options):
        model_class = import_from(options.get('model'))
        serializer_class = import_from(options.get('serializer'))

        self.stdout.write("[")

        start_time = time.time()
        end_num_queries = len(connection.queries)

        queryset = self.get_queryset(model_class, serializer_class)

        if options.get('many'):
            first = True
            for i in queryset.iterator():
                if not first:
                    self.stdout.write(',')

                serializer_instance = serializer_class(instance=i)

                content = json.dumps(
                    serializer_instance.data, cls=encoders.JSONEncoder, ensure_ascii=True
                )
                self.stdout.write(content)
                first = False
        else:
            serializer_instance = serializer_class(instance=queryset, many=True)
            content = json.dumps(
                serializer_instance.data, cls=encoders.JSONEncoder, ensure_ascii=True
            )
            self.stdout.write(content)

        end_time = time.time()
        start_num_queries = len(connection.queries)

        if options.get('query'):
            content = json.dumps(connection.queries, cls=encoders.JSONEncoder, ensure_ascii=True)
            self.stderr.write(content)

        self.stderr.write(
            'OK {0}/{1} {2:.3f}s. Queries count: {3}'.format(
                model_class.__name__,
                serializer_class.__name__,
                end_time - start_time,
                start_num_queries - end_num_queries,
            )
        )

        self.stdout.write("]")
