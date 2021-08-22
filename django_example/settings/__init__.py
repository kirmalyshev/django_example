# encoding=utf-8

import sys

import logging

TESTING = 'test' in sys.argv or 'jenkins' in sys.argv
logging.debug(f"{TESTING=}")
try:
    if TESTING:
        from .testing import *
    else:
        from .local import *
except ImportError:
    from .project import *
