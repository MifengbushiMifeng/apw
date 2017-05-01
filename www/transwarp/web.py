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
            return self[key]
        except KeyError:
            raise AttributeError(r" 'Dict'object has no attribute '%s' " % key)

    def __setattr__(self, key, value):
        self[key] = value


_TIMEDELTA_ZERO = datetime.timedelta(0)
# TODO NEED TO GET THE MEANING OF THE RE
_RE_TZ = re.compile('^([\+\-])([0-9]{1,2})\:([0-9]{1,2})$')


# timezone as UTC+8:00, UTC-10:00
class UTC(datetime.tzinfo):
    def __init__(self, utc):
        utc = str(utc.strip().upper())
        mt = _RE_TZ.match(utc)
        if mt:
            minus = mt.group(1) == '-'
            h = int(mt.group(2))
            m = int(mt.group(3))
            if minus:
                h, m = (-h), (-m)
            self._utcoffset = datetime.timedelta(hours=h, minutes=m)
            self._tzname = 'UTC%s' % utc
        else:
            raise ValueError('bad utc time zone')

    def utcoffset(self, date_time):
        return self._utcoffset

    def dst(self, date_time):
        return _TIMEDELTA_ZERO

    def tzname(self, date_time):
        return self._tzname

    def __str__(self):
        return 'UTC tzinfo object (%s) ' % self._tzname

    __repr__ = __str__()
