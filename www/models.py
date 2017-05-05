# !/usr/bin/env python
# encoding=utf-8
"""
Models for 'user' / 'blog' / 'comment'
"""
import time
import uuid
from transwarp.db import next_id
from transwarp.orm import Model, StringField, BooleanField, FloatField, TextField


# TODO STILL NEEDS TESTING AND BUG FIXED / DAY4
def next_id():
    return '%015d%s000' % (int(time.time() * 1000), uuid.uuid4().hex)


class User(Model):
    __table__ = 'user'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    email = StringField(updateable=False, ddl="varchar(50)")
    password = StringField(ddl='varchar(50)')
    admin = BooleanField
    name = StringField(ddl='varchar(50)')
    image = StringField(ddl='varchar(500)')
    created_at = FloatField(updateable=False, default=time.time)


class Blog(Model):
    __table__ = 'blogs'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    user_id = StringField(updateable=False, ddl='varchar(50)')
    user_name = StringField(ddl='varchar(50)')
    user_image = StringField(ddl='varchar(500)')
    name = StringField(ddl='varchar(50)')
    summary = StringField(ddl='varchar(200)')
    content = TextField()
    created_at = FloatField(updateable=False, default=time.time)


class Comment(Model):
    __table__ = 'comment'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    blog_id = StringField(updateable=False, ddl='varchar(50)')
    user_id = StringField(updateable=False, ddl='varchar(50)')
    user_name = StringField(ddl='varchar(50)')
    user_image = StringField(ddl='varchar(500)')
    content = TextField()
    created_at = FloatField(updateable=False, default=time.time)
