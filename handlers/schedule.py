"""
定时任务处理
TODO: 处理定时任务
"""
import data.log
from haku.alarm import Alarm


class Schedule(object):
    __judge = None
    __alarm: Alarm = None

    def __new__(cls, *args, **kwargs):
        if cls.__judge is None:
            cls.__judge = object.__new__(cls)
        return cls.__judge

    def handle(self):
        if self.__alarm is None:
            self.__alarm = Alarm()
        logger = data.log.get_logger()
        logger.debug(f'Handled alarm {self.__alarm.heart_beat_expired() or self.__alarm.thread_piled_up()}')
