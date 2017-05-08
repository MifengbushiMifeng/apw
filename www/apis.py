#!/usr/bin/env python
# -*- coding: utf-8 -*-
import functools
import json
import logging
from transwarp.web import ctx

"""
JSON API definition
"""

__author__ = 'Jonathan Zhou'


class APIError(StandardError):
    """
    The base APIError which contains error(required), data(optional)
      and message(optional).
    """

    def __init__(self, error, data='', message=''):
        super(APIError, self).__init__(message)
        self.error = error
        self.data = data
        self.message = message


class APIValueError(APIError):
    """
    Indicate the input value has error or invalid.
    The data specifies the error field of input form.
    """

    def __init__(self, field, message=''):
        super(APIValueError, self).__init__('value:invalid', field, message)



class APIPermissionError():
    pass


def api(func):
    @functools.wraps(func)
    def _wrapper(*args, **kw):
        try:
            r = json.dumps(func(*args, **kw))
        except APIError, e:
            pass
        except Exception, e:
            pass
        ctx.response.coontent_type = 'application/json'
        return r

    return _wrapper
