
import os
import sys
import json

__json_path: str


def json_set_config(path: str) -> bool:
    """
    配置 json 文件路径
    :param path: 绝对路径
    :return: 是否成功
    """
    global __json_path
    __json_path = path
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


def json_have_file(path: str) -> bool:
    """
    查找是否存在指定 json 文件
    :param path: 文件名/相对路径
    :return: 存在否
    """
    path = os.path.join(__json_path, path)
    return os.path.exists(path)


def json_load_file(path: str) -> dict:
    """
    读取指定 json 文件
    :param path: 文件名/相对路径
    :return: 文件内容
    """
    path = os.path.join(__json_path, path)
    with open(path, 'r') as fp:
        content = json.load(fp)
    return content


def json_write_file(path: str, content: dict):
    """
    写入指定 json 文件
    :param path: 文件名/相对路径
    :param content: 内容字典
    """
    path = os.path.join(__json_path, path)
    with open(path, 'w') as fp:
        json.dump(content, fp)
