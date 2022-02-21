"""
json 文件读取写入和检测是否存在

用法：
    配置 json 文件目录 : flag = json_set_config(path)
                path 为目录的绝对路径； flag 为是否成功，失败原因可能是不可读写或目标非目录
    判断是否存在 json 文件 : flag = json_have_file(file)
                file 为文件名或相对路径
    读取 json 文件 : content = json_load_file(file)
                content 为 json 文件内容字典
    写入 json 文件 : json_write_file(file, content)
                file 为文件名， content 为内容字典
"""
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


def json_have_file(file: str) -> bool:
    """
    查找是否存在指定 json 文件
    :param file: 文件名/相对路径
    :return: 存在否
    """
    path = os.path.join(__json_path, file)
    return os.path.exists(path)


def json_load_file(file: str) -> dict:
    """
    读取指定 json 文件
    :param file: 文件名/相对路径
    :return: 文件内容
    """
    path = os.path.join(__json_path, file)
    with open(path, 'r') as fp:
        content = json.load(fp)
    return content


def json_write_file(file: str, content: dict):
    """
    写入指定 json 文件
    :param file: 文件名/相对路径
    :param content: 内容字典
    """
    path = os.path.join(__json_path, file)
    with open(path, 'w') as fp:
        json.dump(content, fp)
