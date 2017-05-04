# !/usr/bin/env python
# encoding=utf-8
"""
A simple, lightweight and WSGI-compatible web framework
"""
import os
import threading
import datetime
import re
import urllib
import mimetypes
import cgi

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


def _to_unicode(s, encoding='utf-8'):
    """
    Convert to unicode 
    """
    return s.decode(encoding)


def _quote(s, encoding='utf-8'):
    if isinstance(s, unicode):
        s = s.encode(encoding)
    return urllib.quote(s)


def _unquote(s, encoding='utf-8'):
    return urllib.unquote(s).decode(encoding)


def get(path):
    """
    A 'GET' decorator
    """

    def _decorator(func):
        func.__web_route__ = path
        func.__web_method__ = 'GET'
        return func

    return _decorator


def post(path):
    """
    A 'POST' decorator
    :param path:
    """

    def _decorator(func):
        func.__web_route__ = path
        func.__web_method__ = 'POST'
        return func

    return _decorator


_re_route = re.compile(r'(\:[a-zA-Z_]\w*)')


def _build_regex(path):
    r'''
    Convert route path to regex.

    >>> _build_regex('/path/to/:file')
    '^\\/path\\/to\\/(?P<file>[^\\/]+)$'
    >>> _build_regex('/:user/:comments/list')
    '^\\/(?P<user>[^\\/]+)\\/(?P<comments>[^\\/]+)\\/list$'
    >>> _build_regex(':id-:pid/:w')
    '^(?P<id>[^\\/]+)\\-(?P<pid>[^\\/]+)\\/(?P<w>[^\\/]+)$'
    '''
    re_list = ['^']
    var_list = []
    is_var = False
    for v in _re_route.split(path):
        if is_var:
            var_name = v[1:]
            var_list.append(var_name)
            re_list.append(r'(?P<%s>[^\/]+)' % var_name)
        else:
            s = ''
            for ch in v:
                if ch >= '0' and ch <= '9':
                    s = s + ch
                elif ch >= 'A' and ch <= 'Z':
                    s = s + ch
                elif ch >= 'a' and ch <= 'z':
                    s = s + ch
                else:
                    s = s + '\\' + ch
            re_list.append(s)
        is_var = not is_var
    re_list.append('$')
    return ''.join(re_list)


class Route(object):
    """
    A callable route object
    """

    def __init__(self, func):
        self.path = func.__web_route__
        self.method = func.__web_method__
        self.is_static = _re_route.search(self.path) is None
        if not self.is_static:
            self.route = re.compile(_build_regex(self.path))
        self.func = func

    def match(self, url):
        m = self.route.match(url)
        if m:
            return m.groups()
        return None

    def __call__(self, *args):
        return self.func(*args)

    def __str__(self):
        if self.is_static:
            return 'Route(static, %s, path=%s)' % (self.method, self.path)
        return 'Route(dynamic, %s, path= %s) ' % (self.method, self.path)

    __repr__ = __str__


def _static_file_generator(fpath):
    BLOCK_SIZE = 8192
    with open(fpath, 'rb') as f:
        block = f.read(BLOCK_SIZE)
        while block:
            yield block
            block = f.read(BLOCK_SIZE)


class StaticFileRoute(object):
    def __init__(self):
        self.method = 'GET'
        self.is_static = False
        self.route = re.compile('^/static/(.+)$')

    def match(self, url):
        if url.startwith('/static/'):
            return (url[1:],)
        return None

    def __call__(self, *args):
        fpath = os.path.join(ctx.application.document_root, args[0])
        if not os.path.isfile(fpath):
            raise notfount()
        text = os.path.splitext(fpath)[1]
        ctx.response.content_type = mimetypes.types_map.get(text.lower(), 'application/octet-stream')
        return _static_file_generator(fpath)


def favicon_handler():
    # return static_file_handler('/favicon.ico') TODO
    pass


class MultipartFile(object):
    def __init__(self, storage):
        self.filename = _to_unicode(storage.filename)
        self.file = storage.file


class Request(object):
    """
    Request object for obtaining all http request information.
    """

    def __init__(self, environ):
        self._environ = environ

    def _parse_input(self):
        def _convert(item):
            if isinstance(item, list):
                return [_to_unicode(i.value) for i in item]
            if item.filename:
                return MultipartFile(item)
            return _to_unicode(item.value)

        fs = cgi.FieldStorage(fp=self._environ['wsgi.input'], environ=self._environ, keep_blank_values=True)
        inputs = dict()
        for key in fs:
            inputs[key] = _convert(fs[key])
        return inputs

    def _get_raw_input(self):
        if not hasattr(self, '_raw_input'):
            self._raw_input = self._parse_input()
        return self._raw_input

    def __getitem__(self, key):
        r = self._get_raw_input()[key]
        if isinstance(r, list):
            return r[0]
        return r

    def get(self, key, default=None):
        r = self._get_raw_input().get(key, default)
        if isinstance(r, list):
            return r[0]
        return r

    def gets(self, key):
        r = self._get_raw_input()[key]
        if isinstance(r, list):
            return r[:]
        return [r]

    def input(self, **kw):
        copy = Dict(**kw)
        raw = self._get_raw_input()
        for k, v in raw.iteritems():
            copy[k] = v[0] if isinstance(v, list) else v
        return copy

    def get_body(self):
        fp = self._environ['wsgi.input']
        return fp.read()

    @property
    def remote_addr(self):
        """
        Get the remote address.
        Return 0.0.0.0 if cannot get remote address.
        :return: the remote address
        """
        return self._environ.get('REMOTE_ADDR', '0.0.0.0')

    @property
    def document_root(self):
        return self._environ.get('DOCUMENT_ROOT', '')

    @property
    def query_string(self):
        return self._environ.get('QUERY_STRING', '')

    @property
    def environ(self):
        return self.environ

    @property
    def request_method(self):
        return self._environ['REQUEST_METHOD']

    @property
    def path_info(self):
        return urllib.unquote(self._environ.get('PATH_INFO', ''))

    @property
    def host(self):
        return self._environ.get('HTTP_HOST', '')

    def _get_headers(self):
        if not hasattr(self, '_headers'):
            hdrs = {}
            for k, v in self._environ.iteritems():
                if k.startwith('HTTP_'):
                    hdrs[k[5:].replace('_', '-').upper()] = v.decode('utf-8')
            self._headers = hdrs
            return self._headers

    @property
    def headers(self):
        return dict(**self._get_headers())

    def header(self, header, default=None):
        return self._get_headers().get(header.upper(), default)

    def _get_cookies(self):
        if not hasattr(self, '_cookies'):
            cookies = []
            cookie_str = self._environ.get('HTTP_COOKIE')
            if cookie_str:
                for c in cookie_str.split(';'):
                    pos = c.find('=')
                    if pos > 0:
                        cookies[c[:pos].strip()] = _unquote(c[pos + 1:])
            self._cookies = cookies
        return self._cookies

    @property
    def cookies(self):
        return Dict(**self._get_cookies())

    def cookie(self, name, default=None):
        return self._get_cookies().get(name, default)


UTC_0 = UTC('+00:00')


