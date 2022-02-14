
import os
import sys
import sqlite3

__sqlite_path: str


def sqlite_set_config(path: str) -> bool:
    """
    配置 sqlite3 数据库文件路径
    :param path: 绝对路径
    :return: 是否成功
    """
    global __sqlite_path
    __sqlite_path = path
    if os.path.exists(path):
        if not os.path.isdir(path):
            print('冲突的文件：', path, file=sys.stderr)
            return False
        elif not os.access(path, os.R_OK | os.W_OK):
            print('目录不可读写：', path, file=sys.stderr)
            return False
    else:
        os.mkdir(path, 0o755)
    return True


def sqlite_open_db(path: str) -> sqlite3.Connection:
    """
    读取指定 db 文件
    :param path: 文件名/相对路径
    :return: sqlite3.Connection
    """
    path = os.path.join(__sqlite_path, path)
    conn = sqlite3.connect(path, timeout=20)
    return conn


def sqlite_close_db(conn: sqlite3.Connection):
    """
    关闭指定 db 文件
    :param conn: sqlite3 连接
    """
    conn.commit()
    conn.close()
