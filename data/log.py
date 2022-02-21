"""
全局日志

用法：
    配置全局日志: flag = log_set_config(bot_name, path, console_level, file_level)
                bot_name 为 bot 名称，用于日志记录器命名，
                path 为日志文件目录路径， console_level 为终端日志等级， file_level 为文件记录等级
                配置在 __log_config 中
    获取日志记录器 Logger 对象: get_logger()
"""
import os
import sys
import logging
import logging.config

__all__ = ['get_logger', 'log_set_config']

__log_config = {
    'version': 1,
    'formatters': {
        'default': {
            'format': '[%(asctime)s] %(levelname)s in %(filename)s line %(lineno)d: %(message)s'
        }
    },
    'handlers': {
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'default',
            'filename': './log/haku_bot.log',
            'maxBytes': 1000000,
            'backupCount': 64,
            'level': 'DEBUG',
            'delay': False
        },
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'default'
        },
        # 'flask_file': {
        #     'class': 'logging.handlers.RotatingFileHandler',
        #     'formatter': 'default',
        #     'filename': './hakuBot_flask.log',
        #     'maxBytes': 1000000,
        #     'backupCount': 16,
        #     'level': 'DEBUG',
        #     'delay': False
        # },
        'flask_console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'stream': 'ext://flask.logging.wsgi_errors_stream',
            'formatter': 'default'
        }
    },
    'loggers': dict(),
    'root': {
        'level': 'DEBUG',
        'handlers': ['flask_console', 'file']
    }
}

__bot_name: str
__logger: logging.Logger
__log_levels = ['CRITICAL', 'FATAL', 'ERROR', 'WARNING', 'WARN', 'INFO', 'DEBUG']


def log_set_config(bot_name: str, path: str, console_level: str, file_level: str) -> bool:
    """
    设置全局日志记录器，尽可能早地设置防止失效
    :param bot_name: 名称
    :param path: 文件目录
    :param console_level: 终端打印日志等级
    :param file_level: 日志文件等级
    :return: 是否成功
    """
    global __bot_name, __log_config
    if os.path.exists(path):
        if not os.path.isdir(path):
            print('冲突的文件：', path, file=sys.stderr)
            return False
    else:
        os.mkdir(path, 0o755)
    if len(bot_name) < 1:
        print('不合法的 bot_name ：', bot_name, file=sys.stderr)
        return False
    if console_level not in __log_levels:
        print('不合法的终端日志等级：', console_level, file=sys.stderr)
        return False
    if file_level not in __log_levels:
        print('不合法的日志文件等级：', file_level, file=sys.stderr)
        return False
    __bot_name = bot_name
    __log_config['loggers'] = {
        # bot_name: {
        #     'handlers': ['file', 'console']
        # }
    }
    file_name = os.path.join(path, f'{bot_name}.log')
    if not os.access(path, os.W_OK):
        print('路径不可写：', path, file=sys.stderr)
        return False
    __log_config['handlers']['file']['filename'] = file_name
    __log_config['handlers']['flask_console']['level'] = console_level
    __log_config['handlers']['console']['level'] = console_level
    __log_config['handlers']['file']['level'] = file_level

    __log_set_global()
    return True


def get_logger() -> logging.Logger:
    """
    获取全局 logger
    :return: Logger 对象
    """
    return __logger


def __log_set_global():
    """
    设置全局日志
    """
    global __logger
    logging.config.dictConfig(__log_config)
    __logger = logging.getLogger(__bot_name)
