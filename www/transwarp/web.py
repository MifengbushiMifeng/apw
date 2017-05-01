# !/usr/bin/env python
# encoding=utf-8
"""
A simple, lightweight and WSGI-compatible web framework
"""
import threading
import datetime
import re

# thread local object that for storing requests and responses
ctx = threading.local()


# Dict object
class Dict(dict):
    """
    Simple dict by support access as x.y style
    """

    def __init__(self, names=(), values=(), **kw):
        super(Dict, self).__init__(**kw)
        for k, v in zip(names, values):
            self[k] = v

    def __getattr__(self, key):
        try:
            return self[k]
        except KeyError:
            raise AttributeError(r" 'Dict'object has no attribute '%s' " % key)

    def __setattr__(self, key, value):
        self[key] = value


_TIMEDELTA_ZERO = datetime.timedelta(0)
# TODO NEED TO GET THE MEANING OF THE RE
_RE_TZ = re.compile('^([\+\-])([0-9]{1,2})\:([0-9]{1,2})$')


# timezone as UTC+8:00, UTC-10:00
class UTC(datetime.tzinfo):
    pass
