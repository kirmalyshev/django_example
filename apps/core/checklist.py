# encoding=utf-8

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from collections import deque
from functools import partial


class Checklist(object):
    """
    Offload functions with arguments to initiate their execution later at some point.
    Useful for delaying non-reversible stuff like sending notifications until the very end
    of user request processing (after all possible exceptions have been raised).
    Functions are called in first in, first out order.
    """

    exhausted = False

    def __init__(self):
        self.items = deque()

    def add(self, func, *args, **kwargs):
        """
        Add function to checklist to be called later.
        Function arguments are optional and have to be passed like normal args/kwargs.
        """
        assert callable(func), 'Can only add callables to a checklist'
        self.items.append(partial(func, *args, **kwargs))

    def run(self):
        """
        Run the functions. The callables queue is emptied after that.
        """
        for callee in self.items:
            callee()
        self.items.clear()
