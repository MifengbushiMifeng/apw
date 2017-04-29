# !/usr/bin/env python
# encoding=utf-8
import logging


class Model(dict):
    __metaclass__ = ModelMetaclass

    def __init__(self, **kw):
        super(Model, self).__init__(**kw)

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"Dict object has no attribute '%s'" % key)

    def __setattr__(self, key, value):
        self[key] = value


class ModelMetaclass(type):
    """
    Metaclass for model objects.
    """

    def __new__(cls, name, bases, attrs):
        # skip for the Model class:
        if name == 'Model':
            return type.__new__(cls, name, bases, attrs)

        # store all subclasses info:
        if not hasattr(cls, 'subclasses'):
            cls.subclasses = {}
        if name not in cls.subclasses:
            cls.subclasses[name] = name
        else:
            logging.warning('Redefine class: %s' % name)

        logging.info('Scan ORMapping %s...' % name)
        mapping = dict()
        primary_key = None
        for k, v in attrs.iteritems():
            if isinstance(v, Field):
                pass
