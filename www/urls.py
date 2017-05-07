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


