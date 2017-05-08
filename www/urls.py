# !/usr/bin/env python
# encoding=utf-8
from transwarp.web import get, view, interceptor
from models import User, Blog, Comment
import logging


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
