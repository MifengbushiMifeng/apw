# !/usr/bin/env python
# encoding=utf-8
import threading


# DB Engine Object
class _Engine(object):
    def __init__(self, connect):
        self._connect = connect

    def connect(self):
        return self._connect


engine = None


# ApplicationContext object of the DB connection
class _DbCtx(threading.local):
    pass
