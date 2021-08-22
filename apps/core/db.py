# encoding=utf-8

from __future__ import print_function
from __future__ import unicode_literals

import gc


def queryset_iterator(queryset, chunksize=1000):
    '''''
    Iterate over a Django Queryset ordered by the primary key

    This method loads a maximum of chunksize (default: 1000) rows in it's
    memory at the same time while django normally would load all rows in it's
    memory. Using the iterator() method only causes it to not preload all the
    classes.

    Note that the implementation of the iterator does not support ordered query sets.
    '''
    pk = 0
    last_pk = queryset.order_by('-pk')[0].pk
    queryset = queryset.order_by('pk')
    while pk < last_pk:
        for row in queryset.filter(pk__gt=pk)[:chunksize]:
            pk = row.pk
            yield row
        gc.collect()


def instance_to_python(instance, exclude=tuple()):
    changes = {}
    for field in instance._meta.fields:
        if field.attname in exclude or field.name in exclude:
            continue

        try:
            val = field.to_python(getattr(instance, field.attname))
        except TypeError:
            val = getattr(instance, field.attname)
        changes[field.attname] = val

    return changes
