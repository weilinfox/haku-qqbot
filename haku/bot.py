"""
hakuBot 主体
"""
import sys
import flask
import haku.config


class Bot(object):
    """
    bot 单例类
    hakuBot 主类，实例化 config.Config 和 Flask
    """
    __judge = None
    __config = None
    __flask = None

    def __new__(cls, *args, **kwargs):
        if cls.__judge is None:
            cls.__judge = object.__new__(cls)
        return cls.__judge

    def __init__(self, path: str):
        """
        :param path: main.py 所在目录
        """
        self.__config = haku.config.Config(path)
        self.__flask_debug = False

    def configure(self) -> bool:
        """
        读取并运行配置
        :return: 是否成功
        """
        if not self.__config.configure():
            print('配置没有完成，请检查错误输出后尝试重启~', file=sys.stderr)
            # 这里建立一个 flask 对象来防止后面引用对象时出现异常，其实由于配置没有完成程序即将退出
            self.__flask = flask.Flask('None')
            return False

        # flask 对象
        self.__flask = flask.Flask(self.__config.get_bot_name())
        return True

    def run(self):
        """
        运行 flask 服务器
        """
        self.__flask.run(
            host=self.__config.get_listen_host(),
            port=self.__config.get_listen_port(),
            debug=self.__config.get_flask_debug(),
            threaded=self.__config.get_flask_threaded(),
            processes=1
        )

    def get_flask_obj(self) -> flask.Flask:
        """
        获取 flask 对象
        :return: flask 对象
        """
        return self.__flask