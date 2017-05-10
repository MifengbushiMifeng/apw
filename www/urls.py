# !/usr/bin/env python
# encoding=utf-8
import re
from transwarp.web import get, view, interceptor, post, ctx
from models import User, Blog, Comment
from config import configs
import hashlib
import logging
import time
from apis import api, Page, APIError, APIValueError, APIPermissionError, APIResourceNotFoundError

_COOKIE_NAME = 'awesession'
_COOKIE_KEY = configs.session.secret


def make_signed_cookie(uid, password, max_age):
    # build cookie string by: id-expires-md5
    expires = str(int(time.time() + (max_age or 86400)))
    cookie = [uid, expires, hashlib.md5('%s-%s-%s-%s' % (uid, password, expires, _COOKIE_KEY)).hexdigest()]
    return '-'.join(cookie)


def parse_signed_cookie(cookie_str):
    try:
        L = cookie_str.split('-')
        if len(L) !=3:
            return None

    except:
        return None


@api
@post('/api/users')
def register_user():
    i = ctx.request.input(name='', email='', password='')
    name = i.name.strip()
    email = i.email.strip().lower()
    password = i.password
    if not name:
        raise APIValueError('name')
    if not email or not _RE_EMAIL.match(email):
        raise APIValueError('email')
    if not password or not _RE_MD5.match(password):
        raise APIValueError('password')
    user = User.find_first('where email=?', email)
    if user:
        raise APIError('register:failed', 'email', 'Email is already in use.')
    user = User(name=name, email=email, password=password,
                image='http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email).hexdigest())
    user.insert()
    # make session and cookies
    # cookie = make_signed_cookies()
    return user


@api
@post('/api/authenticate')
def authenticate():
    i = ctx.request.input(remember='')
    email = i.email.strip().lower()
    password = i.password
    remember = i.remember
    user = User.find_first('where email=?', email)
    if user is None:
        raise APIError('auth:failed', 'email', 'Invalid email')
    elif user.password != password:
        raise APIError('auth:failed', 'password', 'Invalid password')
    # make session cookie:
    max_age = 604800 if remember == 'true' else None
    cookie = make_signed_cookie(user.id, user.password, max_age)
    ctx.response.set_cookie(_COOKIE_NAME, cookie, max_age=max_age)
    user.password = '******'
    return user


@view('register.html')
@get('/register')
def register():
    return dict()


@interceptor('/')
def user_interceptor(next):
    logging.info('Try to bind user from session cookie...')
    user = None
    cookie = ctx.request.cookies.get(_COOKIE_NAME)
    if cookie:
        logging.info('parse session cookie')
        user = parse_signed_cookie(cookie)
        if user:
            logging.info('bind user <%s> to session...' % user.email)
    ctx.request.user = user
    return next()


@view('test_users.html')
@get('/')
def test_user():
    users = User.find_all()
    return dict(users=users)


@view('blogs.html')
@get('/test')  # TODO
def index():
    blogs = Blog.find_all()
    # get login user
    user = User.find_first('where email=?', 'admin@example.com')
    return dict(blogs=blogs, user=user)


_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_MD5 = re.compile(r'^[0-9a-f]{32}$')
