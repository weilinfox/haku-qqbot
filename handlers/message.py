"""
消息处理 Message ，插件命令获取
TODO: 复读
插件调用 Plugin ，插件回复消息发送
"""
import re
import importlib
import threading
from typing import Dict, List

import api.gocqhttp
import haku.config
import haku.report
import data.log
import data.json

_plugin_err_code = -1
_plugin_success_code = 1


class Message:
    """
    消息类
    """

    # 嗯这些就是为了复读！
    __group_msg_cache_1 = {}
    __group_msg_cache_2 = {}
    # 特定消息不处理
    __block_msg = [
        '[视频]你的QQ暂不支持查看视频短片，请升级到最新版本后查看。',
    ]

    def __init__(self, message_type: str, sub_type: str, message_id: int, user_id: int):
        """
        :param message_type: 消息类型 group private
        :param sub_type: 子类型 group friend
        :param message_id: 消息 id
        :param user_id: 用户 uid
        """
        self.message_type = message_type
        self.sub_type = sub_type
        self.message_id = message_id
        self.user_id = user_id
        self.group_id = 0
        self.self_id = 0
        self.message = self.raw_message = ''
        self.time = 0
        self.info: dict
        self.reply: str = ''

    def is_group_message(self):
        return self.message_type == 'group'

    def is_private_message(self):
        return self.message_type == 'private' and self.sub_type == 'friend'

    def is_temporary_private_message(self):
        return self.message_type == 'private' and self.sub_type == 'group'

    def handle(self):
        """
        处理消息 判断插件调用 获取插件回复
        """
        if self.message in self.__block_msg:
            return

        # 判断复读！
        repeat = False
        if self.is_group_message():
            new_cache = {'msg': self.message, 'id': self.user_id, 'time': self.time}
            if self.group_id in self.__group_msg_cache_1.keys():
                cached = self.__group_msg_cache_1[self.group_id]
                if self.message == cached['msg'] and self.self_id == cached['id']:
                    pass
                else:
                    self.__group_msg_cache_2[self.group_id] = cached
                    if self.message == cached['msg'] and self.time - cached['time'] < 15:
                        new_cache['id'] = self.self_id
                        repeat = True
                    self.__group_msg_cache_1[self.group_id] = new_cache
            else:
                self.__group_msg_cache_1[self.group_id] = new_cache

        # 判断是否调用插件
        call_plugin = False
        plugin_name = ''
        try:
            index = haku.config.Config().get_index()
            message_sequence = self.message.split()
            plugin_name_judge = r'^{}[_A-Za-z]+$'.format(index)
            if len(message_sequence) <= 0 or len(message_sequence[0]) <= 0:
                return
            com = re.compile(plugin_name_judge)
            if not com.match(message_sequence[0]) is None:
                plugin_name = message_sequence[0][1:]
                call_plugin = True
        except Exception as e:
            data.log.get_logger().exception(f'RuntimeError while checking message: {e}')

        # 调用插件
        if call_plugin:
            plugin = Plugin(plugin_name, self)
            code, self.reply = plugin.handle()
            # 调用插件则不可能复读
            if code == _plugin_success_code:
                repeat = False

        # 复读！
        if repeat:
            api.gocqhttp.send_group_msg(self.group_id, self.message)

    def reply_send(self):
        """
        发送回复消息
        :return:
        """
        if len(self.reply) <= 0:
            return
        if self.is_group_message():
            api.gocqhttp.send_group_msg(self.group_id, self.reply)
        elif self.is_private_message():
            api.gocqhttp.send_private_msg(self.user_id, self.reply)
        elif self.is_temporary_private_message():
            api.gocqhttp.send_temporary_private_msg(self.user_id, self.group_id, self.reply)


class Plugin:
    """
    插件类
    插件首次载入配置： config()
    插件调用： run(Message) -> str
    插件退出： bye()
    """
    __plugin_prefix = 'plugins.commands.'
    __plugin_default_config = {'group_id': [], 'user_id': []}
    __plugin_object_dict: Dict[str, object] = dict()
    __plugin_reload_lock = threading.Lock()

    def __init__(self, name: str = None, message: Message = None):
        if name is None or message is None:
            return
        self.plugin_name = name.strip()
        self.message = message

    def __authorized(self, plugin_name: str) -> bool:
        """
        准入白名单
        :param plugin_name: 插件名
        :return: 是否可以运行
        """
        file = f'{plugin_name}.json'
        if data.json.json_have_file(file):
            my_config = data.json.json_load_file(file)
            try:
                white_group = my_config['group_id']
                white_user = my_config['user_id']
                if len(white_group) != 0 or len(white_user) != 0:
                    # 不为空则开始判断
                    if self.message.is_group_message():
                        if self.message.group_id in white_group or self.message.user_id in white_user:
                            return True
                    elif self.message.is_private_message():
                        if self.message.user_id in white_user:
                            return True
                    return False
            except Exception as e:
                data.log.get_logger().exception(f'RuntimeError while authorizing plugin {plugin_name}: {e}')
                return False
        else:
            data.json.json_write_file(file, self.__plugin_default_config)
        return True

    def handle(self) -> (int, str):
        """
        调用插件并返回回复消息
        :return: 回复消息
        """
        if len(self.plugin_name) <= 0:
            return _plugin_err_code, ''
        return_code = _plugin_success_code
        plugin_name = self.__plugin_prefix + self.plugin_name
        plugin_message = ''

        # 载入插件
        data.log.get_logger().debug(f'Now load plugin {plugin_name}')
        plugin_obj = self.__plugin_object_dict.get(plugin_name)
        if plugin_obj is None:
            try:
                plugin_obj = importlib.import_module(plugin_name)
            except ModuleNotFoundError:
                return_code = _plugin_err_code
                data.log.get_logger().debug(f'No such plugin {plugin_name}')
            else:
                # 记入缓存
                self.__plugin_object_dict.update({plugin_name: plugin_obj})
                # 运行 config()
                if 'config' in dir(plugin_obj):
                    try:
                        plugin_obj.config()
                    except Exception as e:
                        data.log.get_logger().exception(f'RuntimeError while configuring module {plugin_name}: {e}')
        # 成功载入
        if plugin_obj is not None:
            # 权限检查
            if self.__authorized(plugin_name):
                # 运行 run()
                if 'run' in dir(plugin_obj):
                    try:
                        plugin_message = plugin_obj.run(self.message)
                    except Exception as e:
                        data.log.get_logger().exception(f'RuntimeError while running module {plugin_name}: {e}')
            else:
                data.log.get_logger().debug(
                    f'The plugin request from group {self.message.group_id} '
                    f'user {self.message.user_id} was blocked'
                )
        return return_code, plugin_message

    def reload(self):
        """
        插件重载
        """
        with self.__plugin_reload_lock:
            delete_name: List[str] = []
            self.stop()
            for (name, obj) in self.__plugin_object_dict.items():
                try:
                    self.__plugin_object_dict[name] = importlib.reload(obj)
                except ModuleNotFoundError:
                    # 插件已经不存在
                    delete_name.append(name)
                except Exception as e:
                    error_msg = f'RuntimeError while reload module {name}: {e}'
                    data.log.get_logger().exception(error_msg)
                    haku.report.report_send(error_msg)
            for name in delete_name:
                self.__plugin_object_dict.pop(name)

    def stop(self, dead_lock: bool = False):
        """
        插件退出
        :param dead_lock: 之后不再允许插件重载（停止服务时置为 True）
        """
        if dead_lock:
            if not self.__plugin_reload_lock.locked():
                self.__plugin_reload_lock.acquire()
        for obj in self.__plugin_object_dict.values():
            if 'bye' in dir(obj):
                try:
                    obj.bye()
                except Exception as e:
                    data.log.get_logger().exception(f'RuntimeError while quit module {obj.__name__}: {e}')
