"""
向管理群和管理 qq 号发送错误报告
TODO: 邮件支持
"""
from typing import List

import api.gocqhttp
import data.log

admin_group: List[int] = []
admin_user: List[int] = []


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
