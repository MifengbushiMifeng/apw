# !/usr/bin/env python
# encoding=utf-8
import threading
import time
import uuid
import logging
import functools

__author__ = 'Jonathan Zhou'

'''
Database operation module
'''


class Dict(dict):
    """
    A simple dict that can support get attribute as dict.x style 
    >>> d1 = Dict()
    >>> d1['x'] = 100
    >>> d1.x
    100
    >>> d1.y = 200
    >>> d1['y']
    200
    >>> d2 = Dict(a=1, b=2, c='3')
    >>> d2.c
    '3'
    >>> d2['empty']
    Traceback (most recent call last):
        ...
    KeyError: 'empty'
    >>> d2.empty
    Traceback (most recent call last):
        ...
    AttributeError: 'Dict' object has no attribute 'empty'
    >>> d3 = Dict(('a', 'b', 'c'), (1, 2, 3))
    >>> d3.a
    1
    >>> d3.b
    2
    >>> d3.c
    3
    """

    def __init__(self, names=(), values=(), **kw):
        super(Dict, self).__init__(**kw)
        for k, v in zip(names, values):
            self[k] = v

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Dict' object has no attribute '%s' ." % key)

    def __setattr__(self, key, value):
        self[key] = value


def next_id(t=None):
    """
    Return next id as 50-char string.
    
    :param t: system timestamp, default to None and using time.time().
    :return: next id as 50-char string.
    """
    if t is not None:
        t = time.time()

    return '%015d%s000' % (int(t * 1000), uuid.uuid4().hex)


def _profiling(start, sql=''):
    """
    Profiling the sql execute time
    :param start: start time of the sql execution
    :param sql: the execute sql
    :return: None
    """
    t = time.time() - start
    if t > 0.1:
        logging.warning('[PROFILING] [DB] %s: %s' % (t, sql))
    else:
        logging.info('[PROFILING] [DB] %s: %s' % (t, sql))


engine = None


# DB Engine Object
class _Engine(object):
    def __init__(self, connect):
        self._connect = connect

    def connect(self):
        return self._connect


def create_engine(user, password, database, host='127.0.01', port=3306, **kw):
    import mysql.connector
    global engine
    if engine is not None:
        raise DBError('Engine is already initialized.')
    params = dict(user=user, password=password, database=database, host=host, port=port)
    defaults = dict(use_unicode=True, charset='utf8', collation='utf8_general_ci', autocommit=False)
    for k, v in defaults.iteritems():
        params[k] = kw.pop(k, v)
    params.update(kw)
    params['buffered'] = True
    engine = _Engine(lambda: mysql.connector.connect(**params))
    # test connection
    logging.info('Init mysql engine <%s> ok.' % hex(id(engine)))


class DBError(Exception):
    pass


class MultiColumnsError(DBError):
    pass


class _LazyConnection(object):
    def __init__(self):
        self.connection = None

    def cursor(self):
        if self.connection is None:
            con = engine.connect()
            logging.info('open connection <%s>...' % hex(id(con)))
            self.connection = con
        return self.connection.cursor()

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def cleanup(self):
        if self.connection:
            con = self.connection
            self.connection = None
            logging.info('close connection <%s>...' % hex(id(con)))
            con.close()


# ApplicationContext object of the DB connection
class _DbCtx(threading.local):
    """
    Thread Local object that holds connection info 
    """

    def __init__(self):
        self.connection = None
        self.transactions = 0

    def is_init(self):
        return self.connection is not None

    def init(self):
        logging.info('open lazy connection...')
        self.connection = _LazyConnection()
        self.transactions = 0

    def cleanup(self):
        self.connection.cleanup()
        self.connection = None

    def cursor(self):
        # return cursor
        return self.connection.cursor()


_db_ctx = _DbCtx()


# the context of the DB connection
# Will get / release the DB connection auto
class _ConnectionCtx(object):
    """
    _ConnectionCtx object that can open and close connection context. 
    _ConnectionCtx object can be nested and only at the most outer connection has effect.
    
    """

    def __enter__(self):
        global _db_ctx
        self.should_cleanup = False
        if not _db_ctx.is_init():
            _db_ctx.init()
            self.should_cleanup = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):

        global _db_ctx
        if self.should_cleanup:
            _db_ctx.cleanup()


def connection():
    return _ConnectionCtx()


def with_connection(func):
    """
    Decorator for reuse connection
    :param func: the function that will be decorated
    """

    @functools.wraps(func)
    def _wrapper(*args, **kw):
        with _ConnectionCtx():
            return func(*args, **kw)

    return _wrapper


class _TransactionCtx(object):
    """
    _TransactionCtx object that can handle transactions
    """

    def __enter__(self):
        global _db_ctx
        self.should_close_conn = False
        if not _db_ctx.is_init:
            # needs open a connection first:
            _db_ctx.init()
            self.should_close_conn = True
        _db_ctx.transactions += 1
        logging.info('begin transaction...' if _db_ctx.transactions == 1 else 'join current transaction...')

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        global _db_ctx
        _db_ctx.transactions -= 1
        try:
            if _db_ctx.transactions == 0:
                if exc_type is None:
                    self.commit()
                else:
                    self.rollback()

        finally:
            if self.should_close_conn:
                _db_ctx.cleanup()

    def commit(self):
        global _db_ctx

        logging.info('commit transaction...')

        try:
            _db_ctx.connection.commit()

            logging.info('commit ok')
        except:
            logging.warning('commit failed. try rollback...')

            _db_ctx.connection.rollback()

            logging.warning('rollback completed')
            raise

    def rollback(self):
        global _db_ctx

        logging.info('rollback transaction...')

        _db_ctx.connection.rollback()

        logging.info('rollback completed')


def transaction():
    """
    Create a transaction object so can use with statement:

    with transaction():
        pass

    >>> def update_profile(id, name, rollback):
    ...     u = dict(id=id, name=name, email='%s@test.org' % name, passwd=name, last_modified=time.time())
    ...     insert('user', **u)
    ...     r = update('update user set passwd=? where id=?', name.upper(), id)
    ...     if rollback:
    ...         raise StandardError('will cause rollback...')
    >>> with transaction():
    ...     update_profile(900301, 'Python', False)
    >>> select_one('select * from user where id=?', 900301).name
    u'Python'
    >>> with transaction():
    ...     update_profile(900302, 'Ruby', True)
    Traceback (most recent call last):
      ...
    StandardError: will cause rollback...
    >>> select('select * from user where id=?', 900302)
    []
    :return:
    """
    return _TransactionCtx()


def with_transaction(func):
    @functools.wraps(func)
    def _wrapper(*args, **kw):
        _start = time.time()
        with _TransactionCtx:
            return func(*args, **kw)
        _profiling(_start)

    return _wrapper


def _select(sql, first, *args):
    """
    Execute the input sql and then return the results
    :param sql: the sql that want to be executed
    :param first: True means get one record / False means get all records
    :param args: the search result
    :return: 
    """
    global _db_ctx
    cursor = None
    sql = sql.replace('?', '%s')

    logging.info('SQL: %s, ARG %s' % (sql, args))

    try:
        cursor = _db_ctx.connection.cursor()
        cursor.execute(sql, args)
        if cursor.description:
            names = [x[0] for x in cursor.description]
        if first:
            values = cursor.fetchone()
            if not values:
                return None
            return Dict(names, values)
        return [Dict(names, x) for x in cursor.fetchall()]
    finally:
        if cursor:
            cursor.close()


@with_connection
def select_one(sql, *args):
    """
    Execute the sql and return the list or empty if no result.
    If no result found, return None.
    If multiple results found, the first one returned.

    >>> u1 = dict(id=100, name='Alice', email='alice@test.org', passwd='ABC-12345', last_modified=time.time())
    >>> u2 = dict(id=101, name='Sarah', email='sarah@test.org', passwd='ABC-12345', last_modified=time.time())
    >>> insert('user', **u1)
    1
    >>> insert('user', **u2)
    1
    >>> u = select_one('select * from user where id=?', 100)
    >>> u.name
    u'Alice'
    >>> select_one('select * from user where email=?', 'abc@email.com')
    >>> u2 = select_one('select * from user where passwd=? order by email', 'ABC-12345')
    >>> u2.name
    u'Alice'
    """
    return _select(sql, False, *args)


@with_connection
def select_int(sql, *args):
    """
    Execute the sql and expected that one int adn only one int result
    :param sql: the sql that to be executed
    :param args: the params
    :return: the only int result
    """
    d = _select(sql, False, *args)
    if len(d) != 1:
        raise MultiColumnsError('Expect only one column.')
    return d.values()[0]


@with_connection
def select(sql, *args):
    """Execute the sql and return the result."""
    return _select(sql, False, *args)


@with_connection
def _update(sql, *args):
    global _db_ctx
    cursor = None
    sql = sql.replace('?', '%s')
    logging.info('SQL: %s, ARGS: %s' % (sql, args))
    try:
        cursor = _db_ctx.connection.cursor()
        cursor.execute(sql, args)
        r = cursor.rowcount
        if _db_ctx.transactions == 0:
            logging.info('auto commit')
            _db_ctx.connection.commit()
        return r
    finally:
        if cursor:
            cursor.close()


def insert(table, **kw):
    """
    Execute the insert sql.
    :param table: the table that will insert the new record
    :param kw: the data of the new record
    """
    cols, args = zip(kw.iteritems())
    sql = 'INSERT INTO `%s` (%s) VALUES (%s)' % (
        table, ','.join(['`%s`' % col for col in cols]), ','.join(['?' for i in range(len(cols))]))
    return _update(sql, *args)


def update(sql, *args):
    """
    Execute the update sql.
    :param sql: the update sql
    :param args: the params of the sql
    """
    return _update(sql, *args)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    create_engine('www-data', 'www-data', 'test')
    import doctest

    doctest.testmod()
