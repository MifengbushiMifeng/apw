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
