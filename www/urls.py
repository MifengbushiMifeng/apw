# !/usr/bin/env python
# encoding=utf-8
import re
from transwarp.web import get, view, interceptor, post, ctx, view, internalerror, seeother, notfound
from models import User, Blog, Comment
from config import configs
import hashlib
import logging
import time
from apis import api, Page, APIError, APIValueError, APIPermissionError, APIResourceNotFoundError
import markdown2

_COOKIE_NAME = 'awesession'
_COOKIE_KEY = configs.session.secret


def _get_page_index():
    page_index = 1
    try:
        page_index = int(ctx.request.get('page', '1'))
    except ValueError:
        pass
    return page_index


def make_signed_cookie(uid, password, max_age):
    # build cookie string by: id-expires-md5
    expires = str(int(time.time() + (max_age or 86400)))
    cookie = [uid, expires, hashlib.md5('%s-%s-%s-%s' % (uid, password, expires, _COOKIE_KEY)).hexdigest()]
    return '-'.join(cookie)


def parse_signed_cookie(cookie_str):
    try:
        L = cookie_str.split('-')
        if len(L) != 3:
            return None
        id, expires, md5 = L
        if int(expires) < time.time():
            return None
        user = User.get(id)
        if user is None:
            return None
        if md5 != hashlib.md5('%s-%s-%s-%s' % (id, user.password, expires, _COOKIE_KEY)).hexdigest():
            return None
        return user
    except:
        return None


def check_admin():
    user = ctx.request.user
    if user and user.admin:
        return
    raise APIPermissionError('No permission')


@view('signin.html')
@get('/signin')
def signin():
    return dict()


@view('signout')
@get('/signout')
def signout():
    ctx.response.delete_cookie(_COOKIE_NAME)
    raise seeother('/')


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


def _get_blogs_by_page():
    total = Blog.count_all()
    page = Page(total, _get_page_index())
    blogs = Blog.find_all('order by created_at desc limit ?,?', page.offset, page.limit)
    return blogs, page


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


@view('manage_blog_list.html')
@get('/manage/blogs')
def manage_blogs():
    return dict(page_index=_get_page_index(), user=ctx.request.user)


@api
@get('/api/blogs')
def api_get_blogs():
    format = ctx.request.get('format', '')
    blogs, page = _get_blogs_by_page()
    if format == 'html':
        for blog in blogs:
            blog.content = markdown2.markdown(blog.content)
    return dict(blogs=blogs, page=page)


@api
@get('/api/blogs/:blog_id')
def api_get_blog(blog_id):
    blog = Blog.get(blog_id)
    if blog:
        return blog


@api
@post('/api/blogs')
def _api_create_blog():
    check_admin()
    i = ctx.request.input(name='', summary='', content='')
    name = i.name.strip()
    summary = i.summary.strip()
    content = i.content.strip()
    if not name:
        raise APIValueError('name', 'name cannot be empty.')
    if not summary:
        raise APIValueError('summary', 'summary cannot be empty')
    if not content:
        raise APIValueError('content', 'content cannot be empty')
    user = ctx.request.user
    blog = Blog(user_id=user.id, user_name=user.name, name=name, summary=summary, content=content)
    blog.insert()
    return blog


@api
@post('/api/blogs/:blog_id')
def api_update_blog(blog_id):
    check_admin()
    i = ctx.request.input(name='', summary='', content='')
    name = i.name.strip()
    summary = i.summary.strip()
    content = i.content.strip()
    if not name:
        raise APIValueError('name', 'name cannot be empty.')
    if not summary:
        raise APIValueError('summary', 'summary cannot be empty.')
    if not content:
        raise APIValueError('content', 'content cannot be empty.')
    blog = Blog.get(blog_id)
    if blog is None:
        raise APIResourceNotFoundError('Blog')
    blog.name = name
    blog.summary = summary
    blog.content = content
    blog.update()
    return blog


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
