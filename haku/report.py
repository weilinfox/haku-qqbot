"""
向管理群和管理 qq 号发送错误报告
TODO: 邮件支持

用法：
    添加管理群号: report_add_admin_group(group_id)
    添加管理员 qq id : report_add_admin_user(user_id)
    向所有管理群和管理员发送消息: report_send(message)
                message 为消息 str
"""
from typing import List

import requests
import os

import api.gocqhttp
import data.log

admin_group: List[int] = []
admin_user: List[int] = []

gotify_server: str
gotify_token: str


def report_add_admin_group(group_id: int):
    global admin_group
    admin_group.append(group_id)


def report_add_admin_user(user_id: int):
    global admin_user
    admin_user.append(user_id)


def report_send(message: str):
    """
    错误报告发送
    :param message: 错误信息
    """
    for gid in admin_group:
        code, _ = api.gocqhttp.send_group_msg(gid, message)
        if code != 200:
            data.log.get_logger().error(f'Send report ERROR! Error code {code}')
    for uid in admin_user:
        code, _ = api.gocqhttp.send_private_msg(uid, message)
        if code != 200:
            data.log.get_logger().error(f'Send report ERROR! Error code {code}')


def report_gotify_init(url: str, token: str):
    """
    gotify 参数配置
    :param url: gotify 服务器地址
    :param token: gotify 频道 token
    """
    global gotify_server, gotify_token
    gotify_server = os.path.join(url, 'message')
    gotify_token = token


def report_gotify(title: str, message: str):
    """
    gotify 报告
    """
    if gotify_server is None or gotify_token is None:
        return

    params = {'token': gotify_token}
    js = {'message': message, 'title': title}
    try:
        res = requests.post(url=gotify_server, json=js, params=params, timeout=10)
    except:
        data.log.get_logger().exception('Error while report to gotify')
    else:
        if res.status_code != 200:
            data.log.get_logger().error(f'Send gotify ERROR! Response code {res.status_code}')
