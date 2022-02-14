
import signal
from typing import Callable
import data.log


class Alarm(object):
    """
    alarm 单例类
    """
    __judge = None
    __sigalrm_callback: Callable = None
    __duration: int = None
    __heart_enable: bool = None
    __heart_beat_expire: int = 0

    def __new__(cls, *args, **kwargs):
        """
        首次成功初始化后，可以通过不带参数的构造获得成功构造的实例
        """
        if cls.__judge is None or \
                cls.__sigalrm_callback is None or cls.__duration is None or cls.__heart_enable is None:
            cls.__judge = object.__new__(cls)
        return cls.__judge

    def __init__(self, alarm_duration: int = None, heart_beat_enable: bool = None, callback: Callable = None):
        """
        初始化定时器 使用 SIGALRM
        :param alarm_duration: 定时器间隔
        :param heart_beat_enable: cqhttp 是否启用心跳
        :param callback: 定时器定时调用的 回调函数
        """
        if alarm_duration is None or heart_beat_enable is None or callback is None:
            return
        self.__duration = alarm_duration
        self.__heart_enable = heart_beat_enable
        self.__sigalrm_callback = callback
        # 配置
        signal.signal(signal.SIGALRM, self.__new_alarm)
        signal.alarm(alarm_duration)

    def __new_alarm(self, signum, _):
        """
        重启定时器并调用回调
        """
        signal.alarm(self.__duration)
        data.log.get_logger().debug(f'SIGALRM {signum}')
        if self.__heart_beat_expire > 0:
            self.__heart_beat_expire -= self.__duration
        try:
            self.__sigalrm_callback()
        except Exception as e:
            data.log.get_logger().exception(f'RuntimeError while handling SIGALRM: {e}')

    def set_duration(self, duration: int):
        self.__duration = duration

    def new_heart_beat(self, duration: int):
        """
        新的 go-cqhttp 心跳包
        :param duration: 心跳间隔
        """
        self.__heart_beat_expire = duration

    def heart_beat_expired(self) -> bool:
        """
        判断 go-cqhttp 心跳包过期
        :return: 是否已经过期
        """
        if not self.__heart_enable:
            return False
        return self.__heart_beat_expire <= 0
