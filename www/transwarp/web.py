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


# all known responses status
_RESPONSE_STATUSES = {
    # Informational
    100: 'Continue',
    101: 'Switching Protocols',
    102: 'Processing',

    # Successful
    200: 'OK',
    201: 'Created',
    202: 'Accepted',
    203: 'Non-Authoritative Information',
    204: 'No Content',
    205: 'Reset Content',
    206: 'Partial Content',
    207: 'Multi Status',
    226: 'IM Used',

    # Redirection
    300: 'Multiple Choices',
    301: 'Moved Permanently',
    302: 'Found',
    303: 'See Other',
    304: 'Not Modified',
    305: 'Use Proxy',
    307: 'Temporary Redirect',

    # Client Error
    400: 'Bad Request',
    401: 'Unauthorized',
    402: 'Payment Required',
    403: 'Forbidden',
    404: 'Not Found',
    405: 'Method Not Allowed',
    406: 'Not Acceptable',
    407: 'Proxy Authentication Required',
    408: 'Request Timeout',
    409: 'Conflict',
    410: 'Gone',
    411: 'Length Required',
    412: 'Precondition Failed',
    413: 'Request Entity Too Large',
    414: 'Request URI Too Long',
    415: 'Unsupported Media Type',
    416: 'Requested Range Not Satisfiable',
    417: 'Expectation Failed',
    418: "I'm a teapot",
    422: 'Unprocessable Entity',
    423: 'Locked',
    424: 'Failed Dependency',
    426: 'Upgrade Required',

    # Server Error
    500: 'Internal Server Error',
    501: 'Not Implemented',
    502: 'Bad Gateway',
    503: 'Service Unavailable',
    504: 'Gateway Timeout',
    505: 'HTTp Version Not Supported',
    507: 'Insufficient Storage',
    510: 'Noe Extended',
}

_RE_RESPONSE_STATUS = re.compile(r'^\d\d\d(\ [\w\ ]+)?$')

_RESPONSE_HEADERS = {
    'Accept-Ranges',
    'Age',
    'Allow',
    'Cache-Control',
    'Connection',
    'Content-Encoding',
    'Content-Language',
    'Content-Length',
    'Content-Location',
    'Content-MD5',
    'Content-Disposition',
    'Content-Range',
    'Content-Type',
    'Date',
    'ETag',
    'Expires',
    'Last-Modified',
    'Link',
    'Location',
    'P3P',
    'Pragma',
    'Proxy-Authentication',
    'Refresh',
    'Retry-After',
    'Server',
    'Set-Cookie',
    'Strict-Transport-Security',
    'Trailer',
    'Transfer-Encoding',
    'Vary',
    'Via',
    'Warning',
    'WWW-Authenticate',
    'X-Frame-Options',
    'X-XSS-Protection',
    'X_Content-Type-Options',
    'X-Forwarded-Proto',
    'X-Power-By',
    'X_UA_Compatible',
}

_RESPONSE_HEADER_DICT = dict(zip(map(lambda x: x.upper(), _RESPONSE_HEADERS), _RESPONSE_HEADERS))

_HEADER_X_POWERED_BY = ('X-Powered-By', 'transwarp/1.0')


class HTTPError(Exception):
    """
    HTTPError defines the http error codes.
    """

    def __init__(self, code):
        super(HTTPError, self).__init__()
        self.status = '%d %s' % (code, _RESPONSE_STATUSES[code])

    def header(self, name, value):
        if not hasattr(self, '_headers'):
            self._headers = [_HEADER_X_POWERED_BY]
        self._headers.append((name, value))

    @property
    def headers(self):
        if hasattr(self, '_header'):
            return self._headers
        return []

    def __str__(self):
        return self.status

    __repr__ = __str__


class RedirectError(HTTPError):
    """
    RedirectError defines the http redirect codes
    """

    def __init__(self, code, location):
        """
        Init an HtttpError with response code
        :param code: the http error code
        :param location: the redirect location
        """
        super(RedirectError, self).__init__(code)
        self.location = location

    def __str__(self):
        return '%s, %s' % (self.status, self.location)

    __repr__ = __str__


def badresuest():
    """
    Send a 'bad request' error in response
    :return: the 'bad request' response
    """
    return HTTPError(400)


def unauthorized():
    """
    Send a 'unauthorized' error in response
    :return: the 'unauthorized' response
    """
    return HTTPError(401)


def forbidden():
    """
    Send a 'forbidden' error in response
    :return: the 'forbidden' response
    """
    return HTTPError(403)


def notfount():
    """
    Send a 'not found' error in response
    :return: the 'not found' response
    """
    return HTTPError(404)


def conflict():
    """
    Send a 'conflict' error in response
    :return: the 'conflict' response
    """
    return HTTPError(409)


def internalerror():
    """
    Send an 'internal error' in response
    :return: the 'internal error' response
    """
    return HTTPError(500)


def redirect(location):
    """
    Do permanent redirect
    :param location: the location that will be redirect to
    :return: the 'redirect' response
    """
    return RedirectError(301, location)


def found(location):
    """
    Do temporary redirect
    :param location: the location that will be redirect to
    :return: the 'redirect' response
    """
    return RedirectError(302, location)


def seeother(location):
    """
    Do temporary redirect
    :param location: the location that will be redirect to
    :return: the 'redirect' response
    """
    return RedirectError(303, location)


def _to_str(s):
    """
    Convent to string
    :param s: the object that want to convent to string
    :return: the string type value of the input 's'
    """
    if isinstance(s, str):
        return s
    if isinstance(s, unicode):
        return s.encode('utf-8')
    return str(s)
