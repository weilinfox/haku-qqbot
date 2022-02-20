"""
基于 sqlite3 的数据库缓存
根据唯一的模块名获取内存数据库连接
实例化时读取上次存储的缓存
backup 方法将缓存持久化
TODO: 由于当前是一次性读取所有缓存，可以改成需要该表且 sql 语句相同时读取缓存
"""
import sqlite3
from typing import Dict

import data.sqlite
import data.log


class Cache(object):
    """
    缓存 基于 sqlite3 内存数据库
    单例类
    """
    __judge = None
    __databases: Dict[str, sqlite3.Connection] = None
    __database_name = 'bot.cache.db'

    def __new__(cls, *args, **kwargs):
        if cls.__judge is None:
            cls.__judge = object.__new__(cls)
        return cls.__judge

    def __init__(self):
        # 初始化内存数据库
        if self.__databases is not None:
            return
        self.__databases = {}
        # 是否存在缓存
        if not data.sqlite.sqlite_have_db(self.__database_name):
            return
        # 拷贝上次存储的数据
        conn = data.sqlite.sqlite_open_db(self.__database_name)
        cur = conn.cursor()
        # 获取所有数据表
        for table in cur.execute('SELECT name, sql FROM sqlite_master WHERE type=\'table\';'):
            memdb = sqlite3.connect(':memory:')
            # 数据表字典 表名->数据库
            self.__databases[table[0]] = memdb
            memcur = memdb.cursor()
            memcur.execute(table[1])
            title_len = len(cur.execute(f'PRAGMA table_info(\'{table[0]}\');').fetchall())
            insert_com = f'INSERT INTO {table[1]} VALUES({("?,"*title_len)[:-1]});'
            # 拷贝所有数据
            for row in cur.execute(f'SELECT * FROM {table[0]};'):
                memcur.execute(insert_com, row)
            memcur.close()
            memdb.commit()
        # 关闭数据库
        cur.close()
        data.sqlite.sqlite_close_db(conn)

    def backup(self, drop_connection: bool = False):
        """
        将内存数据库备份到磁盘上的单一数据库文件
        :param drop_connection: 是否关闭内存数据库并丢弃数据
        """
        if self.__databases is None:
            data.log.get_logger().warning('Cache database object is None')
            return
        file_db = data.sqlite.sqlite_open_db(self.__database_name)
        backup_db = sqlite3.connect(':memory:')
        try:
            for name, db in self.__databases.items():
                backup_cur = backup_db.cursor()
                cur = db.cursor()
                # 生成语句
                title_len = len(cur.execute(f'PRAGMA table_info(\'{name}\');').fetchall())
                insert_com = f'INSERT INTO {name} VALUES({("?," * title_len)[:-1]});'
                # 建表
                sql_cur = cur.execute(f'SELECT sql FROM sqlite_master WHERE type=\'table\' AND name=\'{name}\';')
                sql = sql_cur.fetchall()[0]
                cur.execute(sql)
                # 插数据
                for row in cur.execute(f'SELECT * FROM {name};'):
                    backup_cur.execute(insert_com, row)
                backup_cur.close()
                # 提交
                backup_db.commit()
        except Exception as e:
            data.log.get_logger().exception(f'RuntimeError while backing up memory database: {e}')
        else:
            backup_db.backup(file_db)
        backup_db.close()
        data.sqlite.sqlite_close_db(file_db)
        # 丢弃内存中的数据库
        if drop_connection:
            for db in self.__databases.values():
                db.close()
            self.__databases = {}

    def get_connection(self, name: str, sql: str) -> sqlite3.Connection:
        """
        根据数据表名 获取内存数据库连接
        :param name: 数据库名
        :param sql: 建表语句
        :return: 数据库 Connection
        """
        if name not in self.__databases.keys():
            conn = sqlite3.connect(':memory:')
            cur = conn.cursor()
            cur.execute(sql)
            cur.close()
            conn.commit()
            self.__databases[name] = conn
            return conn
        return self.__databases[name]
