"""
go-cqhttp api
原始文档 https://docs.go-cqhttp.org/api/ 或 https://github.com/ishkong/go-cqhttp-docs
TODO: 完成剩余的 api

用法：
    初始化 api : cqhttp_init(url, token)
            url 为 go-cqhttp 上报地址， token 为上报口令
    调用 api : 查看代码
"""
import requests
import re
import sys
import os
import traceback
from typing import Union

import data.log

__post_url: str
__post_params: dict
__request_err: int = -1
__message_err_id: int = 0


def cqhttp_init(url: str, token: str) -> bool:
    """
    初始化发送消息的 url 和 go-cqhttp 需要的 token
    :param url: 地址
    :param token: 口令
    :return: 是否配置成功
    """
    global __post_url, __post_params
    tag = r'https?://[^:\s]+:[0-9]+/?$'
    if not re.compile(tag).match(url):
        print(f'不合法的 post_url : {url} ， post_url 形如 http://127.0.0.1:8000/', file=sys.stderr)
        return False
    if token is None:
        print(f'注意接收到的 token 为 None ， 重置为空字符串')
        token = ''
    __post_url = url
    __post_params = {'access_token': token}
    return True


def __send_requests(endpoint: str, params: dict) -> (int, dict):
    """
    发送 go-cqhttp 请求
    :param endpoint: 终结点
    :param params: 参数
    :return: http 状态码，响应数据
    """
    url = os.path.join(__post_url, endpoint)
    params.update(__post_params)
    data.log.get_logger().debug(f'Send message to {url}: {params}')
    try:
        resp = requests.get(url=url, params=params, timeout=10)
        ans = (resp.status_code, resp.json())
        data.log.get_logger().debug(f'Get response: {ans[1]}')
    except Exception as e:
        data.log.get_logger().exception(f'RuntimeError while processing get request: {e}')
        ans = (__request_err, {'error_msg': traceback.format_exc()})

    return ans


def __parse_message_response(code: int, resp: dict) -> (int, int):
    """
    解析发送消息的响应数据，字段仅有 message_id
    go-cqhttp 状态码也会转换为 http 状态码
    get retcode and message_id, if retcode != 200 do not use that message_id!
    :param code: request http status code
    :param resp: response dict {'data': {'message_id': -510749883}, 'retcode': 0, 'status': 'ok'}
    :return: retcode, message_id
    """
    if code == 200 and resp.get('retcode') == 0:
        msg_id = resp.get('data').get('message_id')
        # 返回 200 代码 和有效的 message_id
        return code, msg_id
    elif code == __request_err:
        # 这里截取到 get request 出错返回，后面不要处理 message_id
        return code, __message_err_id
    else:
        code = resp.get('retcode')
        if code is None:
            code = 500
        # 返回 go-cqhttp 错误代码，后面不要处理 message_id
        return code, __message_err_id


def send_private_msg(user_id: int, message: str, auto_escape: bool = False) -> (int, int):
    """
    发送私聊消息
    :param user_id: 对方 QQ 号
    :param message: 要发送的内容
    :param auto_escape: 是否不解析 CQ 码
    :return: http 状态码，消息 ID
    """
    params = {'user_id': user_id, 'message': message, 'auto_escape': auto_escape}
    code, resp = __send_requests('send_private_msg', params)
    return __parse_message_response(code, resp)


def send_temporary_private_msg(user_id: int, group_id: int, message: str, auto_escape: bool = False) -> (int, int):
    """
    发送临时群消息
    :param user_id: 对方 QQ 号
    :param group_id: 主动发起临时会话群号
    :param message: 要发送的内容
    :param auto_escape: 是否不解析 CQ 码
    :return: http 状态码，消息 ID
    """
    params = {'user_id': user_id, 'group_id': group_id, 'message': message, 'auto_escape': auto_escape}
    code, resp = __send_requests('send_private_msg', params)
    return __parse_message_response(code, resp)


def send_group_msg(group_id: int, message: str, auto_escape: bool = False) -> (int, int):
    """
    发送群消息
    :param group_id: 群号
    :param message: 要发送的内容
    :param auto_escape: 是否不解析 CQ 码
    :return: http 状态码，消息 ID
    """
    params = {'group_id': group_id, 'message': message, 'auto_escape': auto_escape}
    code, resp = __send_requests('send_group_msg', params)
    return __parse_message_response(code, resp)


def send_group_share_music(group_id: int, music_type: str, music_id: Union[int, str]) -> (int, int):
    """
    发送私聊音乐分享
    :param group_id: 群 id
    :param music_type: 类型
    :param music_id: 曲目 id
    :return: http 状态码，消息 ID
    """
    if not (music_type in ['qq', '163', 'xm']):
        return 404, 0
    return send_group_msg(group_id, f'[CQ:music,type={music_type},id={music_id}]')


def send_private_share_music(user_id: int, music_type: str, music_id: Union[int, str]) -> (int, int):
    """
    发送群音乐分享
    :param user_id: qq id
    :param music_type: 类型
    :param music_id:  曲目 id
    :return: http 状态码，消息 ID
    """
    if not (music_type in ['qq', '163', 'xm']):
        return 404, 0
    return send_private_msg(user_id, f'[CQ:music,type={music_type},id={music_id}]')


def send_group_forward_msg(group_id: int, message: str) -> int:
    """
    关于 message 查看 https://docs.go-cqhttp.org/api/#%E5%8F%91%E9%80%81%E5%90%88%E5%B9%B6%E8%BD%AC%E5%8F%91-%E7%BE%A4
    :param group_id: 群 id
    :param message: forward node[]
    :return: http 状态码
    """
    params = {'group_id': group_id, 'message': message}
    res, _ = __send_requests('send_group_forward_msg', params)
    return res


def send_msg(message_type: str, message: str, user_id: int = 0, group_id: int = 0, auto_escape: bool = False) \
        -> (int, int):
    """
    发送消息
    :param message_type: group/private
    :param message: 消息
    :param user_id: message_type 为 private 时需要
    :param group_id: message_type 为 group 时需要
    :param auto_escape: 是否不解析 CQ 码
    :return: http 状态码，消息 ID
    """
    params = {'message_type': message_type, 'message': message, 'user_id': user_id, 'group_id': group_id,
              'auto_escape': auto_escape}
    code, resp = __send_requests('send_msg', params)
    return __parse_message_response(code, resp)


def delete_msg(message_id: int) -> int:
    """
    撤回消息
    :param message_id: 消息 id
    :return: http 状态码
    """
    params = {'message_id': message_id}
    res, _ = __send_requests('delete_msg', params)
    return res


def get_msg(message_id: int) -> int:
    """
    获取消息
    :param message_id: 消息 id
    :return: http 状态码
    """
    params = {'message_id': message_id}
    res, _ = __send_requests('get_msg', params)
    return res


def get_forward_msg(message_id: int) -> (int, dict):
    """
    获取合并转发内容
    :param message_id: 消息 id
    :return: http 状态码, 消息字典
    """
    params = {'message_id': message_id}
    return __send_requests('get_forward_msg', params)


def get_image(file: str) -> (int, dict):
    """
    获取图片信息
    :param file: 图片缓存文件名
    :return: http 状态码, 消息字典
    """
    params = {'file': file}
    return __send_requests('get_image', params)


def group_kick(group_id: int, user_id: int, reject_add_request: bool) -> int:
    """
    群组踢人
    :param group_id: 群号
    :param user_id: 要踢的 qq 号
    :param reject_add_request: 拒绝此人的加群请求
    :return: http 状态码
    """
    params = {'group_id': group_id, 'user_id': user_id, 'reject_add_request': reject_add_request}
    ret, _ = __send_requests('set_group_kick', params)
    return ret


def group_ban(group_id: int, user_id: int, duration: int) -> int:
    """
    群组单人禁言
    :param group_id: 群号
    :param user_id: 要禁言的 qq 号
    :param duration: 禁言时长 秒
    :return: http 状态码
    """
    params = {'group_id': group_id, 'user_id': user_id, 'duration': duration}
    ret, _ = __send_requests('set_group_ban', params)
    return ret


def group_ban_cancel(group_id: int, user_id: int) -> int:
    """
    群组单人禁言
    :param group_id: 群号
    :param user_id: 要解除禁言的 qq 号
    :return: http 状态码
    """
    params = {'group_id': group_id, 'user_id': user_id, 'duration': 0}
    ret, _ = __send_requests('set_group_ban', params)
    return ret


def group_anonymous_ban(group_id: int, anonymous: Union[dict, str], duration: int) -> int:
    """
    群组匿名用户禁言
    :param group_id: 群号
    :param anonymous: 要禁言的匿名用户对象 或要禁言的匿名用户的flag
    :param duration: 禁言时长 秒
    :return: http 状态码
    """
    params = {'group_id': group_id, 'duration': duration}
    if isinstance(anonymous, dict):
        params.update({'anonymous': anonymous})
    elif isinstance(anonymous, str):
        params.update({'anonymous_flag': anonymous})
    else:
        return 404
    ret, _ = __send_requests('set_group_anonymous_ban', params)
    return ret


def group_whole_ban(group_id: int) -> int:
    """
    群组全员禁言
    :param group_id: 群号
    :return: http 状态码
    """
    params = {'group_id': group_id, 'enable': True}
    ret, _ = __send_requests('set_group_whole_ban', params)
    return ret


def group_whole_ban_cancel(group_id: int) -> int:
    """
    群组取消全员禁言
    :param group_id: 群号
    :return: http 状态码
    """
    params = {'group_id': group_id, 'enable': False}
    ret, _ = __send_requests('set_group_whole_ban', params)
    return ret


def set_group_anonymous(group_id: int, enable: bool) -> int:
    """
    设置群组匿名 注 go-cqhttp 未支持
    :param group_id: 群号
    :param enable: 是否允许
    :return: http 状态码
    """
    params = {'group_id': group_id, 'enable': enable}
    ret, _ = __send_requests('set_group_whole_ban', params)
    return ret


def set_group_card(group_id: int, user_id: int, card: str) -> int:
    """
    设置群员备注
    :param group_id: 群号
    :param user_id: 要设置的 qq 号
    :param card: 群备注（空字符串则删除群备注）
    :return: http 状态码
    """
    params = {'group_id': group_id, 'user_id': user_id, 'card': card}
    ret, _ = __send_requests('set_group_card', params)
    return ret


def set_group_name(group_id: int, group_name: str) -> int:
    """
    设置群名
    :param group_id: 群号
    :param group_name: 群名
    :return: http 状态码
    """
    params = {'group_id': group_id, 'group_name': group_name}
    ret, _ = __send_requests('set_group_name', params)
    return ret


def group_leave(group_id: int) -> int:
    """
    退出群组
    :param group_id: 群号
    :return: http 状态码
    """
    params = {'group_id': group_id, 'is_dismiss': False}
    ret, _ = __send_requests('set_group_leave', params)
    return ret


def group_dismiss(group_id: int) -> int:
    """
    解散群组 bot必须是群主 否则将退出该群组
    :param group_id: 群号
    :return: http 状态码
    """
    params = {'group_id': group_id, 'is_dismiss': True}
    ret, _ = __send_requests('set_group_leave', params)
    return ret


def set_group_special_title(group_id: int, user_id: int, special_title: str) -> int:
    """
    设置群组专属头衔
    :param group_id: 群号
    :param user_id: 要设置的 qq 号
    :param special_title: 专属头衔
    :return: http 状态码
    """
    params = {'group_id': group_id, 'user_id': user_id, 'special_title': special_title, 'duration': -1}
    ret, _ = __send_requests('set_group_special_title', params)
    return ret


def set_friend_add_request(flag: str, approve: bool, remark: str = '') -> int:
    """
    处理加好友请求
    :param flag: 加好友请求的 flag
    :param approve: 是否同意
    :param remark: 同意添加后的好友备注
    :return: http 状态码
    """
    params = {'flag': flag, 'approve': approve}
    if approve and len(remark) > 0:
        params.update({'remark': remark})
    ret, _ = __send_requests('set_friend_add_request', params)
    return ret


def set_group_add_request(flag: str, sub_type: str, approve: bool, reason: str = '') -> int:
    """
    处理加群请求/邀请
    :param flag: 加群请求的 flag
    :param sub_type: 请求类型（add 或 invite）
    :param approve: 是否同意
    :param reason: 如果拒绝的拒绝理由
    :return: http 状态码
    """
    params = {'flag': flag, 'sub_type': sub_type, 'approve': approve}
    if not approve and len(reason) > 0:
        params.update({'reason': reason})
    ret, _ = __send_requests('set_group_add_request', params)
    return ret
