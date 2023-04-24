"""
检测配置文件和目录，对缺失配置文件写入默认配置
读取 bot 所有的配置文件，并根据配置文件配置各个模块

用法：
    初始化配置: config = Config(path)
            不允许重复初始化
    获取实例: config = Config()
    运行配置: flag = config.configure()
            flag 判断是否配置成功
    获取配置参数: obj = config.get_*()
            obj 获取配置的值，配置不存在将返回默认配置
"""
import os
import sys
import yaml
from typing import List

import api.gocqhttp
import data.log
import data.json
import data.sqlite
import haku.report

_DEFAULT_CONFIG = {
    "server_config": {
        "listen_host": "127.0.0.1",
        "listen_port": 8000,
        "post_url": "http://127.0.0.1:8001/",
        "access_token": "",
        "flask_threads": True,
        "flask_debug": False,
        "file_log_level": "INFO",
        "console_log_level": "INFO"
    },
    "bot_config": {
        "bot_name": "haku_bot",
        "admin_qq": [],
        "admin_group": [],
        "index": ".",
        "index_cn": "#"
    }
}

_DEFAULT_KEYS = {
    'sample1': 'key1',
    'sample2': 'key2',
}


class Config(object):
    """
    bot 配置 单例类
    读取 config.yaml 和 keys.yaml 并初始化 bot
    """
    __name = 'haku_bot'
    __root_path: str = None
    __path: str = None
    __config_path = ''
    __key_path = ''
    __server_config: dict
    __bot_config: dict
    __bot_keys: dict
    __gotify_config: dict
    __judge = None

    def __new__(cls, *args, **kwargs):
        if cls.__judge is None or cls.__judge.__path is None:
            cls.__judge = object.__new__(cls)
        return cls.__judge

    def __init__(self, path: str = None):
        """
        首次成功初始化后，可以通过不带参数的构造获得成功构造的实例
        :param path: main.py 所在目录
        """
        if path is None or self.__root_path is not None:
            return
        self.__root_path = path
        self.__path = f'{path}/files'
        self.__config_path = os.path.join(self.__path, 'config.yaml')
        self.__key_path = os.path.join(self.__path, 'keys.yaml')

    def configure(self) -> bool:
        """
        读取配置文件并配置 data 模块
        :return: 是否成功
        """
        # 读取配置
        if not self.__read_config():
            return False

        # 配置 data 模块
        json_path = os.path.join(self.__path, 'json')
        sqlite_path = os.path.join(self.__path, 'sqlite')
        log_path = os.path.join(self.__path, 'log')
        if not data.log.log_set_config(
                self.__name,
                log_path,
                self.__server_config['console_log_level'],
                self.__server_config['file_log_level']
        ):
            return False
        if not data.json.json_set_config(json_path):
            return False
        if not data.sqlite.sqlite_set_config(sqlite_path):
            return False

        # 配置 report
        qq_list = self.get_admin_qq_list()
        grp_list = self.get_admin_group_list()
        if isinstance(qq_list, list):
            for uid in qq_list:
                haku.report.report_add_admin_user(uid)
        if isinstance(grp_list, list):
            for gid in grp_list:
                haku.report.report_add_admin_group(gid)

        # 配置 api
        if not api.gocqhttp.cqhttp_init(self.get_post_url(), self.get_access_token()):
            return False

        print(f'{self.__name} 配置完成')
        return True

    def get_root_path(self) -> str:
        return self.__root_path

    def get_listen_host(self) -> str:
        return self.__server_config['listen_host']

    def get_listen_port(self) -> int:
        return self.__server_config['listen_port']

    def get_post_url(self) -> str:
        return self.__server_config['post_url']

    def get_access_token(self) -> str:
        return self.__server_config['access_token']

    def get_flask_threaded(self) -> bool:
        return self.__server_config.get('flask_threads', True)

    def get_flask_debug(self) -> bool:
        return self.__server_config.get('flask_debug', False)

    def get_file_log_level(self) -> str:
        return self.__server_config.get('file_log_level', 'INFO')

    def get_console_log_level(self) -> str:
        return self.__server_config.get('console_log_level', 'INFO')

    def get_admin_qq_list(self) -> List[int]:
        return self.__bot_config.get('admin_qq')

    def get_admin_group_list(self) -> List[int]:
        return self.__bot_config.get('admin_group')

    def get_bot_name(self) -> str:
        return self.__name

    def get_index(self) -> str:
        return self.__bot_config['index']

    def get_index_cn(self) -> str:
        return self.__bot_config.get('index_cn', "#")

    def get_key(self, name: str) -> str:
        return self.__bot_keys.get(name, '')

    def get_gotify_config(self) -> dict:
        return self.__gotify_config

    def get_gotify_enabled(self) -> bool:
        return self.__gotify_config is not None

    def __read_config(self) -> bool:
        """
        读取配置文件并判断合法性
        :return:
        """
        # 扫描文件
        global _DEFAULT_CONFIG, _DEFAULT_KEYS
        if os.path.exists(self.__path):
            if not os.path.isdir(self.__path):
                print('冲突的文件：', self.__path, file=sys.stderr)
                return False
        else:
            if not os.access(os.path.dirname(self.__path), os.W_OK):
                print('无法建立目录：', self.__path, '，没有写入权限')
                return False
            os.mkdir(self.__path, 0o755)
        file_check = _check_file(self.__config_path, _DEFAULT_CONFIG, True)
        file_check = _check_file(self.__key_path, _DEFAULT_KEYS) and file_check
        if not file_check:
            return False

        # 读取
        try:
            config_dict = yaml_read_file(self.__config_path)
            self.__bot_keys = yaml_read_file(self.__key_path)
        except Exception as e:
            print(e, file=sys.stderr)
            return False

        # 合法性
        if 'server_config' not in config_dict.keys():
            print('无法找到 server_config 服务配置', file=sys.stderr)
            return False
        if 'bot_config' not in config_dict.keys():
            print('无法找到 haku_config 配置', file=sys.stderr)
            return False
        self.__server_config = config_dict['server_config']
        self.__bot_config = config_dict['bot_config']
        gotify_config = config_dict.get('gotify')
        if gotify_config is not None:
            print('发现 gotify 配置')
            if 'server' in gotify_config.keys() and 'token' in gotify_config.keys():
                haku.report.report_gotify_init(gotify_config['server'], gotify_config['token'])
                # 缓存 gotify 配置
                self.__gotify_config = gotify_config
            else:
                print('gotify 配置不合法', file=sys.stderr)
        server_config_keys = self.__server_config.keys()
        bot_config_keys = self.__bot_config.keys()
        if 'index' not in bot_config_keys:
            print('无法找到 bot_config->index 指令前缀配置', file=sys.stderr)
            return False
        index = self.__bot_config['index']
        if len(index) != 1:
            print('不合法的前缀长度：', len(index), file=sys.stderr)
            return False
        if 'bot_name' in bot_config_keys and len(self.__bot_config['bot_name']) > 0:
            self.__name = self.__bot_config['bot_name']
        if 'listen_host' not in server_config_keys or 'listen_port' not in server_config_keys or \
                'post_url' not in server_config_keys or 'access_token' not in server_config_keys:
            return False

        return True


def _check_file(path: str, default_content: dict, escape: bool = False) -> bool:
    """
    检查所需的配置文件，如果不存在建立并写入默认配置
    :param path: 配置文件路径
    :param default_content: 默认配置
    :param escape: 文件缺失是否影响继续配置
    :return: 是否成功
    """
    if os.path.exists(path):
        if not os.path.isfile(path):
            print('冲突的文件：', path, file=sys.stderr)
            return False
        elif not os.access(path, os.R_OK):
            print('文件不可读：', path, file=sys.stderr)
            return False
    else:
        if not os.access(os.path.dirname(path), os.W_OK):
            print('文件不可写：', path, file=sys.stderr)
            return False
        yaml_write_file(path, default_content)
        print('建立缺失的配置文件，请按实际更改：', path, file=sys.stderr)
        if escape:
            return False
    return True


def yaml_read_file(path: str) -> dict:
    content: dict
    with open(path, 'r') as fp:
        content = yaml.load(fp.read(), Loader=yaml.Loader)
    return content


def yaml_write_file(path: str, content: dict):
    with open(path, 'w', encoding='utf-8') as fp:
        yaml.dump(content, fp)
