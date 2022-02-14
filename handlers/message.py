
import re
import importlib
import threading
from typing import Dict, List

import haku.config
import haku.report
import data.log
import data.json


class Message:
    """
    消息类
    """
    def __init__(self, message_type: str, sub_type: str, message_id: int, user_id: int):
        self.message_type = message_type
        self.sub_type = sub_type
        self.message_id = message_id
        self.user_id = user_id
        self.group_id = 0
        self.message = self.raw_message = ''
        self.time = 0
        self.info: dict
        self.reply: str = ''

    def is_group_message(self):
        return self.message_type == 'group'

    def is_private_message(self):
        return self.message_type == 'private'

    def handle(self):
        """
        处理消息 判断插件调用 获取插件回复
        """
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
        else:
            if not call_plugin:
                return

        # 调用插件
        plugin = Plugin(plugin_name, self)
        self.reply = plugin.handle()

    def reply_send(self):
        """
        发送回复消息
        :return:
        """
        if len(self.reply) <= 0:
            return
        pass


class Plugin:
    """
    插件类
    插件首次载入配置： config()
    插件调用： run(Message) -> str
    插件退出： quit()
    """
    __plugin_prefix = 'plugins.commands.'
    __plugin_default_config = {'group_id': [0, ], 'user_id': [0, ]}
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
        file = f'{str}.json'
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

    def handle(self) -> str:
        """
        调用插件并返回回复消息
        :return: 回复消息
        """
        if len(self.plugin_name) <= 0:
            return ''
        plugin_name = self.__plugin_prefix + self.plugin_name
        plugin_message = ''
        if self.__authorized(plugin_name):
            data.log.get_logger().debug(f'Now execute plugin {plugin_name}')
            plugin_obj = self.__plugin_object_dict.get(plugin_name)
            if plugin_obj is None:
                try:
                    plugin_obj = importlib.import_module(plugin_name)
                except ModuleNotFoundError:
                    data.log.get_logger().debug(f'No such plugin {self.plugin_name}')
                else:
                    # 记入缓存
                    self.__plugin_object_dict.update({plugin_name: plugin_obj})
                    # 运行 config()
                    if 'config' in dir(plugin_obj):
                        try:
                            plugin_obj.config(self.message)
                        except Exception as e:
                            data.log.get_logger().exception(f'RuntimeError while configuring module {plugin_name}: {e}')
            # 成功载入 运行 run()
            if plugin_obj is not None:
                if 'run' in dir(plugin_obj):
                    try:
                        plugin_message = plugin_obj.run(self.message)
                    except Exception as e:
                        data.log.get_logger().exception(f'RuntimeError while running module {plugin_name}: {e}')
        else:
            data.log.get_logger().debug(f'The plugin request from group {self.message.group_id} \
user {self.message.user_id} was blocked')
        return plugin_message

    def reload(self):
        with self.__plugin_reload_lock:
            delete_name: List[str] = []
            for obj in self.__plugin_object_dict.values():
                # 插件退出
                if 'quit' in dir(obj):
                    try:
                        obj.quit()
                    except Exception as e:
                        data.log.get_logger().exception(f'RuntimeError while quit module {obj.__name__}: {e}')
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
