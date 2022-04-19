"""
go-cqhttp api
原始文档 https://docs.go-cqhttp.org/api/ 或 https://github.com/ishkong/go-cqhttp-docs
cqcode 文档 https://docs.go-cqhttp.org/cqcode/
TODO: fix api bug 添加一些 cqcode 函数

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
from typing import Union, List

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


def set_friend_add_request(flag: str, approve: bool, remark: str = None) -> int:
    """
    处理加好友请求
    :param flag: 加好友请求的 flag
    :param approve: 是否同意
    :param remark: 同意添加后的好友备注
    :return: http 状态码
    """
    params = {'flag': flag, 'approve': approve}
    if approve and remark is not None:
        params.update({'remark': remark})
    ret, _ = __send_requests('set_friend_add_request', params)
    return ret


def set_group_add_request(flag: str, sub_type: str, approve: bool, reason: str = None) -> int:
    """
    处理加群请求/邀请
    :param flag: 加群请求的 flag
    :param sub_type: 请求类型（add 或 invite）
    :param approve: 是否同意
    :param reason: 如果拒绝的拒绝理由
    :return: http 状态码
    """
    params = {'flag': flag, 'sub_type': sub_type, 'approve': approve}
    if not approve and reason is not None:
        params.update({'reason': reason})
    ret, _ = __send_requests('set_group_add_request', params)
    return ret


def get_login_info() -> (int, dict):
    """
    获取登录号信息
    :return: http 状态码, 消息字典
    """
    return __send_requests('get_login_info', {})


def qidian_get_account_info() -> (int, dict):
    """
    获取企点账号信息
    :return: http 状态码, 消息字典
    """
    return __send_requests('qidian_get_account_info', {})


def get_stranger_info(user_id: int, no_cache: bool = False) -> (int, dict):
    """
    获取陌生人信息
    :param user_id: qq id
    :param no_cache: 是否不使用缓存（使用缓存可能更新不及时 但响应更快）
    :return: http 状态码, 消息字典
    """
    params = {'user_id': user_id, 'no_cache': no_cache}
    return __send_requests('get_stranger_info', params)


def get_friend_list() -> (int, dict):
    """
    获取好友列表
    :return: http 状态码, 消息字典
    """
    return __send_requests('get_friend_list', {})


def delete_friend(friend_id: int) -> int:
    """
    删除好友
    :return: http 状态码
    """
    params = {'friend_id': friend_id}
    ret, _ = __send_requests('delete_friend', params)
    return ret


def get_group_info(group_id: int, no_cache: bool = False) -> (int, dict):
    """
    获取好友列表
    :param group_id: 群号
    :param no_cache: 是否不使用缓存（使用缓存可能更新不及时 但响应更快）
    :return: http 状态码, 消息字典
    """
    params = {'group_id': group_id, 'no_cache': no_cache}
    return __send_requests('get_group_info', params)


def get_group_image_url(group_id: int) -> str:
    """
    获取群头像链接
    :param group_id: 群号
    :return: 图片链接
    """
    return f'https://p.qlogo.cn/gh/{group_id}/{group_id}/100'


def get_group_list() -> (int, dict):
    """
    获取群列表
    :return: http 状态码, 消息字典
    """
    return __send_requests('get_group_list', {})


def get_group_member_info(group_id: int, user_id: int, no_cache: bool = False) -> (int, dict):
    """
    获取群成员信息
    :param group_id: 群号
    :param user_id: 要查看的 qq 号
    :param no_cache: 是否不使用缓存（使用缓存可能更新不及时 但响应更快）
    :return: http 状态码, 消息字典
    """
    params = {'group_id': group_id, 'user_id': user_id, 'no_cache': no_cache}
    return __send_requests('get_group_member_info', params)


def get_group_member_list(group_id: int) -> (int, dict):
    """
    获取群成员列表
    :param group_id: 群号
    :return: http 状态码, 消息字典
    """
    params = {'group_id': group_id}
    return __send_requests('get_group_member_list', params)


def get_group_honor_info(group_id: int, sub_type: str) -> (int, dict):
    """
    获取群荣誉信息
    :param group_id: 群号
    :param sub_type: 要获取的群荣誉类型 talkative performer legend strong_newbie emotion 分别获取或 all 获取所有数据
    :return: http 状态码, 消息字典
    """
    params = {'group_id': group_id, 'type': sub_type}
    return __send_requests('get_group_honor_info', params)


def get_cookies(domain: str) -> (int, dict):
    """
    获取 Cookies go-cqhttp 未支持
    :param domain: 需要获取 cookies 的域名
    :return: http 状态码, 消息字典
    """
    params = {'domain': domain}
    return __send_requests('get_cookies', params)


def get_csrf_token(domain: str) -> (int, dict):
    """
    获取 CSRF Token go-cqhttp 未支持
    :return: http 状态码, 消息字典
    """
    return __send_requests('get_csrf_token', {})


def get_credentials(domain: str) -> (int, dict):
    """
    获取 QQ 相关接口凭证（get_cookies 和 get_csrf_token） go-cqhttp 未支持
    :param domain: 需要获取 cookies 的域名
    :return: http 状态码, 消息字典
    """
    return __send_requests('get_credentials', {})


def get_record(file: str, out_format: str) -> (int, dict):
    """
    获取语音 go-cqhttp 未支持
    :param file: 收到的语音文件名
    :param out_format: 要转换到的格式
    :return: http 状态码, 消息字典
    """
    params = {'file': file, 'out_format': out_format}
    return __send_requests('get_credentials', params)


def can_send_image() -> (int, bool):
    """
    检查是否可以发送图片
    :return: http 状态码, 是或否
    """
    ret, can = __send_requests('can_send_image', {})
    return ret, can['yes']


def can_send_record() -> (int, bool):
    """
    检查是否可以发送语音
    :return: http 状态码, 是或否
    """
    ret, can = __send_requests('can_send_record', {})
    return ret, can['yes']


def get_version_info() -> (int, dict):
    """
    获取版本信息
    :return: http 状态码, 消息字典
    """
    return __send_requests('get_version_info', {})


def set_restart(delay: int = 0) -> (int, dict):
    """
    重启 go-cqhttp
    :param delay: 延迟毫秒数 如果默认情况下无法重启 可以尝试设置延迟为 2000 左右
    :return: http 状态码, 消息字典
    """
    params = {'delay': delay}
    return __send_requests('get_credentials', params)


def clean_cache() -> int:
    """
    清理缓存 go-cqhttp 未支持
    :return: http 状态码
    """
    ret, _ = __send_requests('clean_cache', {})
    return ret


def set_group_portrait(group_id: int, file: str, cache: bool = True) -> int:
    """
    设置群头像 目前这个API在登录一段时间后因cookie失效而失效 请考虑后使用
    :param group_id: 群号
    :param file: 图片文件 url 或 base64
    :param cache: 是否使用已缓存的文件 通过网络 URL 发送时有效
    :return: http 状态码
    """
    params = {'group_id': group_id, 'file': file, cache: 1 if cache else 0}
    ret, _ = __send_requests('set_group_portrait', params)
    return ret


def get_word_slices(content: str) -> (int, List[str]):
    """
    获取中文分词 隐藏api 不建议一般用户使用
    :param content: 内容
    :return: http 状态码, 消息字典
    """
    params = {'content': content}
    ret, slices = __send_requests('.get_word_slices', params)
    return ret, slices['slices']


def ocr_image(image: str) -> (int, dict):
    """
    图片 OCR
    :param image: 图片 ID
    :return: http 状态码, 消息字典
    """
    params = {'image': image}
    return __send_requests('ocr_image', params)


def get_group_system_msg() -> (int, dict):
    """
    获取群系统消息
    :return: http 状态码, 消息字典
    """
    return __send_requests('get_group_system_msg', {})


def upload_group_file(group_id: int, file: str, name: str, folder: str = None) -> int:
    """
    上传群文件
    :param group_id: 群号
    :param file: 本地文件绝对路径
    :param name: 储存名称
    :param folder: 父目录ID 不提供则为根目录
    :return: http 状态码
    """
    params = {'group_id': group_id, 'file': file, 'name': name}
    if folder is not None:
        params.update({'folder': folder})
    ret, _ = __send_requests('upload_group_file', params)
    return ret


def get_group_file_system_info(group_id: int) -> (int, dict):
    """
    获取群文件系统信息
    :param group_id: 群号
    :return: http 状态码, 消息字典
    """
    params = {'group_id': group_id}
    return __send_requests('get_group_file_system_info', params)


def get_group_root_files(group_id: int) -> (int, dict):
    """
    获取群根目录文件列表
    :param group_id: 群号
    :return: http 状态码, 消息字典
    """
    params = {'group_id': group_id}
    return __send_requests('get_group_root_files', params)


def get_group_files_by_folder(group_id: int, folder_id: str) -> (int, dict):
    """
    获取群子目录文件列表
    :param group_id: 群号
    :param folder_id: 目录 ID
    :return: http 状态码, 消息字典
    """
    params = {'group_id': group_id, 'folder_id': folder_id}
    return __send_requests('get_group_files_by_folder', params)


def get_group_file_url(group_id: int, file_id: str, busid: int) -> (int, str):
    """
    获取群文件资源链接
    :param group_id: 群号
    :param file_id: 文件 ID
    :param busid: 文件类型
    :return: http 状态码, 消息字典
    """
    params = {'group_id': group_id, 'file_id': file_id, 'busid': busid}
    ret, url = __send_requests('get_group_files_by_folder', params)
    return ret, url['url']


def get_status() -> (int, dict):
    """
    获取状态
    :return: http 状态码, 消息字典
    """
    return __send_requests('get_status', {})


def get_group_at_all_remain(group_id: int) -> (int, dict):
    """
    获取群 @全体成员 剩余次数
    :param group_id: 群号
    :return: http 状态码, 消息字典
    """
    params = {'group_id': group_id}
    return __send_requests('get_status', params)


def quick_operation(context: dict, operation: dict) -> int:
    """
    执行快速操作 隐藏api 不建议一般用户使用
    :param context: 事件数据对象
    :param operation: 快速操作对象
    :return: http 状态码
    """
    params = {'context': context, 'operation': operation}
    ret, _ = __send_requests('.handle_quick_operation', params)
    return ret


def get_vip_info(user_id: int) -> (int, dict):
    """
    获取VIP信息
    :param user_id: 用户 qq id
    :return: http 状态码, 消息字典
    """
    params = {'user_id': user_id}
    return __send_requests('_get_vip_info', params)


def send_group_notice(group_id: int, content: str, image: str = None) -> int:
    """
    发送群公告
    :param group_id: 群号
    :param content: 公告内容
    :param image: 图片路径（可选）
    :return: http 状态码
    """
    params = {'group_id': group_id, 'content': content}
    if image is not None:
        params.update({'image': image})
    ret, _ = __send_requests('_send_group_notice', params)
    return ret


def reload_event_filter(file: str) -> int:
    """
    重载事件过滤器
    :param file: 事件过滤器文件
    :return: http 状态码
    """
    params = {'file': file}
    ret, _ = __send_requests('reload_event_filter', params)
    return ret


def download_file(url: str, headers: Union[str, List[str]], thread_count: int = 1) -> (int, dict):
    """
    下载文件到缓存目录 调用后会阻塞直到下载完成后才会返回数据
    :param url: 链接地址
    :param headers: 自定义请求头
    :param thread_count: 下载线程数
    :return: http 状态码, 消息字典
    """
    params = {'url': url, 'headers': headers, 'thread_count': thread_count}
    return __send_requests('reload_event_filter', params)


def get_online_clients(no_cache: bool = False) -> (int, dict):
    """
    获取当前账号在线客户端列表
    :param no_cache: 是否无视缓存
    :return: http 状态码, 消息字典
    """
    params = {'no_cache': no_cache}
    return __send_requests('get_online_clients', params)


def get_group_msg_history(group_id: int, message_seq: int = None) -> (int, dict):
    """
    获取群消息历史记录
    :param group_id: 群号
    :param message_seq: 起始消息序号 不提供起始序号将默认获取最新的消息
    :return: http 状态码, 消息字典
    """
    params = {'group_id': group_id}
    if message_seq is not None:
        params.update({'message_seq': message_seq})
    return __send_requests('get_group_msg_history', params)


def set_essence_msg(message_id: int) -> int:
    """
    设置精华消息
    :param message_id: 消息 id
    :return: http 状态码, 消息字典
    """
    params = {'message_id': message_id}
    ret, _ = __send_requests('set_essence_msg', params)
    return ret


def delete_essence_msg(message_id: int) -> int:
    """
    移除精华消息
    :param message_id: 消息 id
    :return: http 状态码, 消息字典
    """
    params = {'message_id': message_id}
    ret, _ = __send_requests('delete_essence_msg', params)
    return ret


def get_essence_msg_list(group_id: int) -> (int, dict):
    """
    获取精华消息列表
    :param group_id: 群号
    :return: http 状态码, 消息字典
    """
    params = {'group_id': group_id}
    return __send_requests('get_essence_msg_list', params)


def check_url_safely(url: str) -> (int, dict):
    """
    检查链接安全性
    :param url: 需要检查的链接
    :return: http 状态码, 消息字典（level 安全等级 1 安全 2 未知 3 危险）
    """
    params = {'url': url}
    return __send_requests('check_url_safely', params)


def get_model_show(model: str) -> (int, dict):
    """
    获取在线机型
    :param model: 机型名称
    :return: http 状态码, 消息字典
    """
    params = {'model': model}
    return __send_requests('_get_model_show', params)


def set_model_show(model: str, model_show: str) -> int:
    """
    获取在线机型
    :param model: 机型名称
    :param model_show: -
    :return: http 状态码
    """
    params = {'model': model, 'model_show': model_show}
    ret, _ = __send_requests('_set_model_show', params)
    return ret


""" 一些 cqcode 帮助函数 """


def parse_cqcode_record(url: str, cache: bool = True) -> str:
    """
    语音 cq 码
    :param url: 语音文件名/url
    :param cache: 是否使用已缓存的文件 url 发送有效
    :return: cqcode
    """
    if cache:
        return f'[CQ:record,file={url}]'
    else:
        return f'[CQ:record,file={url},cache=0]'


def parse_cqcode_image(url: str, cache: bool = True) -> str:
    """
    图片 cq 码
    :param url: 图片文件名/url
    :param cache: 是否使用已缓存的文件 url 发送有效
    :return: cqcode
    """
    if cache:
        return f'[CQ:image,file={url}]'
    else:
        return f'[CQ:image,file={url},cache=0]'


def parse_cqcode_face(fid: int) -> str:
    """
    语音 cq 码
    :param fid: 表情 id
    :return: cqcode
    """
    return f'[CQ:face,id={fid}]'
