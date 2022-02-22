#!/usr/bin/python3
"""
bot 启动脚本
"""
import os.path
import signal
import sys
import threading
import time
from typing import List

import flask

import data.log
import haku.report
from handlers.message import Message
from handlers.schedule import Schedule
from handlers.misc import Misc
from haku.bot import Bot
from haku.alarm import Alarm

version = 'v0.0.1-beta'
bot = Bot(os.path.dirname(__file__))
can_run = bot.configure()
stop_flag = False
app = bot.get_flask_obj()
bot_pid = os.getpid()

__flask_threads: List[threading.Thread] = []
__flask_thread_max = 100

if can_run:
    logger = data.log.get_logger()


def __signal_sigint_handler(signum, _):
    print('收到 sigint', signum, ' 退出', file=sys.stderr)
    exit(0)


def __quitter(delay_sec: int):
    time.sleep(delay_sec)
    logger.info('Quit bot now')
    os.kill(bot_pid, signal.SIGINT)


def __parse_message(raw_message_dict: dict):
    try:
        message_type = raw_message_dict['message_type']
        sub_type = raw_message_dict['sub_type']
        # 不处理 anonymous 匿名和 notice 管理员禁止/允许群内匿名聊天
        if message_type == 'group' and sub_type != 'normal':
            return
        # 不处理 group_self 群中自身发送和 other 其他
        if message_type == 'private' and sub_type == 'group_self' or sub_type == 'other':
            return
        message = Message(message_type, sub_type, raw_message_dict['message_id'], raw_message_dict['user_id'])
        message.message = raw_message_dict['message']
        message.raw_message = raw_message_dict['raw_message']
        if message_type == 'group':
            message.group_id = raw_message_dict['group_id']
        message.time = raw_message_dict['time']
        message.self_id = raw_message_dict['self_id']
        data.log.get_logger().debug(f'Get message: {raw_message_dict}')
    except Exception as e:
        logger.exception(f'RuntimeError while parsing message: {e}')
        return
    # 处理 message
    message.handle()
    message.reply_send()


def __parse_notice(raw_message_dict: dict):
    notice_type = raw_message_dict['notice_type']
    if notice_type == 'group_upload':
        pass
    elif notice_type == 'group_admin':
        pass
    elif notice_type == 'group_decrease':
        pass
    elif notice_type == 'group_increase':
        pass
    elif notice_type == 'group_ban':
        pass
    elif notice_type == 'friend_add':
        pass
    elif notice_type == 'group_recall':
        pass
    elif notice_type == 'friend_recall':
        pass
    elif notice_type == 'notify':
        sub_type = raw_message_dict['sub_type']
        if sub_type == 'poke':
            pass
        elif sub_type == 'lucky_king':
            pass
        elif sub_type == 'honor':
            pass
    elif notice_type == 'group_card':
        pass
    elif notice_type == 'offline_file':
        pass
    elif notice_type == 'client_status':
        pass
    elif notice_type == 'essence':
        pass


def __parse_request(raw_message_dict: dict):
    request_type = raw_message_dict['request_type']
    if request_type == 'friend':
        pass
    elif request_type == 'group':
        sub_type = raw_message_dict['sub_type']
        if sub_type == 'add':
            pass
        elif sub_type == 'invite':
            pass


def __parse_meta_event(raw_message_dict: dict):
    try:
        event_type = raw_message_dict.get('meta_event_type', '')
        interval = raw_message_dict.get('interval', -1)
        if event_type == 'heartbeat' and interval != -1:
            logger.debug(f'Get heartbeat with interval {interval}ms')
            interval //= 1000
            alarm.new_heart_beat(interval)
    except Exception as e:
        logger.exception(f'RuntimeError while handling meta_event: {e}')


def __parse_requests(raw_message_dict: dict):
    """
    处理请求并分发
    :param raw_message_dict: 原始消息字典
    """
    support_type = ['message', 'notice', 'request', 'meta_event']
    post_type = raw_message_dict.get('post_type', '')
    if post_type not in support_type:
        return
    if post_type == 'message':
        __parse_message(raw_message_dict)
    elif post_type == 'notice':
        __parse_notice(raw_message_dict)
    elif post_type == 'request':
        __parse_request(raw_message_dict)
    elif post_type == 'meta_event':
        __parse_meta_event(raw_message_dict)


@app.route('/', methods=['POST', 'GET'])
def route_message() -> str:
    global __flask_threads
    if stop_flag:
        return ''
    try:
        raw_message_dict = flask.request.get_json()
    except Exception as e:
        logger.exception(f'RuntimeError while parsing request: {e}')
    else:
        new_thread = threading.Thread(target=__parse_requests, args=[raw_message_dict], daemon=True)
        new_thread.start()
        __flask_threads.append(new_thread)
    # 清理 thread list
    dead_thread: List[threading.Thread] = []
    for i in range(len(__flask_threads)):
        if not __flask_threads[i].is_alive():
            dead_thread.append(__flask_threads[i])
    for obj in dead_thread:
        __flask_threads.remove(obj)
        logger.debug(f'Remove flask thread: {obj}')
    thread_count = len(__flask_threads)
    logger.debug(f'Flask thread count: {thread_count}')

    # 线程过多上报
    if thread_count > __flask_thread_max:
        haku.report.report_send(f'Threads in haku qqbot piled up: {thread_count}')

    return ''


@app.route('/handler', methods=['GET'])
def route_handler() -> str:
    return 'handler'


@app.route('/threads', methods=['GET'])
def thread_info() -> str:
    return f'{len(__flask_threads)}'


@app.route('/stop', methods=['GET'])
def stop_bot() -> str:
    global stop_flag
    stop_flag = True
    bot.stop()
    delay_sec = 5
    threading.Thread(target=__quitter, args=(delay_sec, ), daemon=True).start()
    return 'stop'


@app.route('/version', methods=['GET'])
def get_version() -> str:
    return version


if __name__ == '__main__':
    if can_run:
        signal.signal(signal.SIGINT, __signal_sigint_handler)
        alarm = Alarm(1, True, Schedule().handle)
        bot.run()
    else:
        print('初始化不成功', file=sys.stderr)
