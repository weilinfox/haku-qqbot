import sqlite3
import threading
# from typing import Union
import data.sqlite
import data.log


class Cache(object):
    """
    缓存 基于 sqlite3 内存数据库
    """
    __judge = None
    # __database: Union[sqlite3.Connection, None] = None
    __database = None
    __thread_lock = threading.Lock()
    __database_lock = threading.Lock()
    __database_name = 'bot.cache.db'

    def __new__(cls, *args, **kwargs):
        if cls.__judge is None:
            cls.__judge = object.__new__(cls)
        return cls.__judge

    def __init__(self):
        # 初始化内存数据库
        if self.__database is not None:
            return
        self.__database = sqlite3.connect(':memory:')
        # 拷贝上次存储的数据
        conn = data.sqlite.sqlite_open_db(self.__database_name)
        cur = conn.cursor()
        cur.execute('SELECT name FROM sqlite_master;')
        name = cur.fetchall()[0]
        cur.close()
        if len(name) > 0:
            conn.backup(self.__database)
        data.sqlite.sqlite_close_db(conn)

    def backup(self, drop_connection: bool = False):
        """
        将内存数据库备份到磁盘
        :param drop_connection: 是否关闭内存数据库并丢弃数据
        """
        if self.__database is None:
            data.log.get_logger().warning('Cache database object is None')
            return
        conn = data.sqlite.sqlite_open_db(self.__database_name)
        cache = self.get_connection()
        cache.backup(conn)
        self.close_connection(drop_connection)
        data.sqlite.sqlite_close_db(conn)

    def get_connection(self) -> sqlite3.Connection:
        """
        获取内存数据库连接，得到数据库使用权
        :return: 数据库 Connection ，如果为空则 None
        """
        # 获取锁
        with self.__thread_lock:
            self.__database_lock.acquire()
        if self.__database is None:
            self.__init__()
        return self.__database

    def close_connection(self, drop_connection: bool = False):
        """
        提交数据，释放数据库使用权
        :param drop_connection: 是否关闭内存数据库并丢弃数据
        """
        self.__database.commit()
        if drop_connection:
            self.__database.close()
            self.__database = None
        with self.__thread_lock:
            if self.__database_lock.locked():
                self.__database_lock.release()
            else:
                data.log.get_logger().warning('Cache database thread lock is not locked')
