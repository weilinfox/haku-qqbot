"""
定时任务触发
任务线程数量监控和堆积上报
心跳包个数监控和缺失上报
"""
import signal
import threading
from typing import Callable
import data.log
import haku.report


class Alarm(object):
    """
    alarm 单例类
    实现 hakuBot 的定时任务功能
    """
    __judge = None
    __sigalrm_callback: Callable = None
    __duration: int = None
    __heart_enable: bool = None
    __heart_beat_expire: int = 60
    __thread_list = []
    __thread_list_warn_len = 5
    __thread_list_lock = threading.Lock()
    __warn_delay = 24 * 3600

    def __new__(cls, *args, **kwargs):
        """
        首次成功初始化后，可以通过不带参数的构造获得成功构造的实例
        """
        if cls.__judge is None or cls.__judge.__sigalrm_callback is None or \
                cls.__judge.__duration is None or cls.__judge.__heart_enable is None:
            cls.__judge = object.__new__(cls)
        return cls.__judge

    def __init__(self, alarm_duration: int = None, heart_beat_enable: bool = None, callback: Callable = None):
        """
        初始化定时器 使用 SIGALRM
        :param alarm_duration: 定时器间隔 秒
        :param heart_beat_enable: cqhttp 是否启用心跳
        :param callback: 定时器定时调用的 回调函数
        """
        if alarm_duration is None or heart_beat_enable is None or callback is None:
            return
        self.__duration = alarm_duration
        self.__heart_enable = heart_beat_enable
        self.__sigalrm_callback = callback
        self.__thread_piled_up_warn_delay = 0
        self.__heart_beat_expire_warn_delay = 0
        # 配置
        signal.signal(signal.SIGALRM, self.__new_alarm)
        signal.alarm(alarm_duration)

    def __new_alarm(self, signum, _):
        """
        重启定时器并调用回调
        """
        signal.alarm(self.__duration)
        data.log.get_logger().debug(f'SIGALRM {signum}')
        if self.__heart_beat_expire >= 0:
            self.__heart_beat_expire -= self.__duration
        # 新线程调用回调 线程对象加入列表
        try:
            new_thread = threading.Thread(target=self.__sigalrm_callback, daemon=True)
            self.__thread_list.append(new_thread)
            new_thread.start()
        except Exception as e:
            data.log.get_logger().exception(f'RuntimeError while handling SIGALRM: {e}')
        # 列表移除已经退出的线程
        with self.__thread_list_lock:
            dead_thread = []
            for obj in self.__thread_list:
                if isinstance(obj, threading.Thread):
                    if not obj.is_alive():
                        dead_thread.append(obj)
                else:
                    data.log.get_logger().warning(f'Found strange object in thread list: {obj}')
                    dead_thread.append(obj)
            for obj in dead_thread:
                data.log.get_logger().debug(f'Remove SIGALRM handler thread: {obj}')
                self.__thread_list.remove(obj)
        # 线程过多上报 由于多每秒一次 SIGALRM 所以线程数应该比较少
        if self.thread_piled_up():
            if self.__thread_piled_up_warn_delay <= 0:
                self.__thread_piled_up_warn_delay = self.__warn_delay
                warn_msg = f'Thread in class Alarm piled up: thread count {len(self.__thread_list)}'
                data.log.get_logger().warning(f'Send report: {warn_msg}')
                haku.report.report_send(warn_msg)
            else:
                self.__thread_piled_up_warn_delay -= self.__duration
        # 心跳过期报告
        if self.heart_beat_expired():
            # 实现第一次发现过期不报告，第二次再报告，即等待一个 duration 再报告
            if self.__heart_beat_expire_warn_delay < 0:
                self.__heart_beat_expire_warn_delay = self.__warn_delay
                warn_msg = f'Heartbeat expired in class Alarm: thread count {len(self.__thread_list)}'
                data.log.get_logger().warning(f'Send report: {warn_msg}')
                haku.report.report_send(warn_msg)
            elif self.__heart_beat_expire_warn_delay == 0:
                # 已经过期，等待一次
                self.__heart_beat_expire_warn_delay -= self.__duration
            else:
                self.__heart_beat_expire_warn_delay -= self.__duration
                # 无法减到 <0
                if self.__heart_beat_expire_warn_delay < 0:
                    self.__heart_beat_expire_warn_delay = 0
        elif self.__heart_beat_expire_warn_delay < 0:
            # 等待一次的过程中恢复心跳，复位 delay
            self.__heart_beat_expire_warn_delay = 0

    def set_duration(self, duration: int):
        """
        设置 SIGALRM 间隔 秒
        :param duration: 间隔 秒
        """
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
        return self.__heart_beat_expire < 0

    def thread_piled_up(self) -> bool:
        return len(self.__thread_list) > self.__thread_list_warn_len
