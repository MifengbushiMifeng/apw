# !/usr/bin/env python
# encoding=utf-8
import re
from transwarp.web import get, view, interceptor, post, ctx
from models import User, Blog, Comment
from config import configs
import hashlib
import logging

from apis import api, Page, APIError, APIValueError, APIPermissionError, APIResourceNotFoundError

_COOKIE_NAME = 'awesession'
_COOKIE_KEY = configs.session.secret


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
