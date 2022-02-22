"""
定时任务处理
TODO: 处理定时任务

用法：
    获取实例 : schedule = Schedule()
    载入/更新数据库 : schedule.data_load()
    检查并执行定时任务 : schedule.handle()
    定时任务的插入删除参考 plugins.commands.schedules 插件和 plugins.commands.commands 插件
"""
import threading
import time
from typing import Dict, Union, List

import api.gocqhttp
import data.log
import data.sqlite
import haku.report
import haku.config
import handlers.message


class Schedule(object):
    __judge = None
    __reload_delay = 15
    __db_name = 'handlers.schedule.db'
    __minute = time.gmtime(time.time() + 8 * 3600).tm_min - 1
    __data_reload_delay = 0

    # interval -> [{'user_id': int, 'command': str, 'delay': int}]
    __commands_group_dict: Dict[int, List[Dict[str, Union[str, int]]]] = {}
    __commands_private_dict: Dict[int, List[Dict[str, Union[str, int]]]] = {}
    __commands_lock = threading.Lock()
    # MMdd -> [{'user_id': int, 'message': str}]
    __by_date_group_dict: Dict[int, List[Dict[str, Union[str, int]]]] = {}
    __by_date_private_dict: Dict[int, List[Dict[str, Union[str, int]]]] = {}
    # hhmm -> [{'user_id': int, 'message': str}]
    __by_time_group_dict: Dict[int, List[Dict[str, Union[str, int]]]] = {}
    __by_time_private_dict: Dict[int, List[Dict[str, Union[str, int]]]] = {}
    __schedules_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls.__judge is None:
            cls.__judge = object.__new__(cls)
            # 数据库初始化
            conn = data.sqlite.sqlite_open_db(cls.__db_name)
            cur = conn.cursor()
            # interval minute, type private/group ，方便处理，所有命令不带前缀
            cur.execute('CREATE TABLE IF NOT EXISTS '
                        'commands(type text, user_id int, group_id int, command text, interval int);')
            cur.execute('CREATE TABLE IF NOT EXISTS '
                        'bydate(type text, user_id int, group_id int, month int, day int, message text);')
            cur.execute('CREATE TABLE IF NOT EXISTS '
                        'bytime(type text, user_id int, group_id int, hour int, minute int, message text);')
            cur.close()
            data.sqlite.sqlite_close_db(conn)
        return cls.__judge

    def data_load(self):
        """
        载入数据库
        """
        data.log.get_logger().debug('Schedule loading database')
        __commands_group_dict: Dict[int, List[Dict[str, Union[str, int]]]] = {}
        __commands_private_dict: Dict[int, List[Dict[str, Union[str, int]]]] = {}
        __by_date_group_dict: Dict[int, List[Dict[str, Union[str, int]]]] = {}
        __by_date_private_dict: Dict[int, List[Dict[str, Union[str, int]]]] = {}
        __by_time_group_dict: Dict[int, List[Dict[str, Union[str, int]]]] = {}
        __by_time_private_dict: Dict[int, List[Dict[str, Union[str, int]]]] = {}
        conn = data.sqlite.sqlite_open_db(self.__db_name)
        try:
            cur = conn.cursor()
            # commands
            for row in cur.execute('SELECT interval, user_id, command FROM commands WHERE type=\'private\';'):
                if row[0] in __commands_private_dict.keys():
                    __commands_private_dict[row[0]].append({'user_id': row[1], 'command': row[2], 'delay': row[0]})
                else:
                    __commands_private_dict[row[0]] = [{'user_id': row[1], 'command': row[2], 'delay': row[0]}]
            for row in cur.execute('SELECT interval, user_id, group_id, command FROM commands WHERE type=\'group\';'):
                if row[0] in __commands_group_dict.keys():
                    __commands_group_dict[row[0]].append({'user_id': row[1], 'group_id': row[2], 'command': row[3],
                                                          'delay': row[0]})
                else:
                    __commands_group_dict[row[0]] = [{'user_id': row[1], 'group_id': row[2], 'command': row[3],
                                                      'delay': row[0]}]
            # by date
            for row in cur.execute('SELECT month, day, user_id, message FROM bydate WHERE type=\'private\';'):
                key = row[0] * 100 + row[1]
                if key in __by_date_private_dict.keys():
                    __by_date_private_dict[key].append({'user_id': row[2], 'message': row[3]})
                else:
                    __by_date_private_dict[key] = [{'user_id': row[2], 'message': row[3]}, ]
            for row in cur.execute('SELECT month, day, user_id, group_id, message FROM bydate WHERE type=\'group\';'):
                key = row[0] * 100 + row[1]
                if key in __by_date_group_dict.keys():
                    __by_date_group_dict[key].append({'user_id': row[2], 'group_id': row[3], 'message': row[4]})
                else:
                    __by_date_group_dict[key] = [{'user_id': row[2], 'group_id': row[3], 'message': row[4]}, ]
            # by time
            for row in cur.execute('SELECT hour, minute, user_id, message FROM bytime WHERE type=\'private\';'):
                key = row[0] * 100 + row[1]
                if key in __by_time_private_dict.keys():
                    __by_time_private_dict[key].append({'user_id': row[2], 'message': row[3]})
                else:
                    __by_time_private_dict[key] = [{'user_id': row[2], 'message': row[3]}, ]
            for row in cur.execute('SELECT hour, minute, user_id, group_id, message FROM bytime '
                                   'WHERE type=\'group\';'):
                key = row[0] * 100 + row[1]
                if key in __by_time_group_dict.keys():
                    __by_time_group_dict[key].append({'user_id': row[2], 'group_id': row[3], 'message': row[4]})
                else:
                    __by_time_group_dict[key] = [{'user_id': row[2], 'group_id': row[3], 'message': row[4]}, ]
        except Exception as e:
            msg = f'RuntimeError while reload schedule data: {e}'
            data.log.get_logger().exception(msg)
            haku.report.report_send(msg)
        else:
            self.__commands_group_dict = __commands_group_dict
            self.__commands_private_dict = __commands_private_dict
            self.__by_date_group_dict = __by_date_group_dict
            self.__by_date_private_dict = __by_date_private_dict
            self.__by_time_group_dict = __by_time_group_dict
            self.__by_time_private_dict = __by_time_private_dict
        data.sqlite.sqlite_close_db(conn)
        data.log.get_logger().debug('Schedule load database finished')

    def handle(self):
        """
        定时任务处理
        """
        time_now = time.gmtime(time.time() + 8 * 3600)
        logger = data.log.get_logger()
        logger.debug(f'Handled alarm: {time_now.tm_hour}:{time_now.tm_min}:{time_now.tm_sec}')
        # 一分钟只触发一次
        if time_now.tm_min == self.__minute:
            return

        self.__minute = time_now.tm_min
        self.__data_reload_delay -= 1
        # 重载数据库
        if self.__data_reload_delay <= 0:
            self.__data_reload_delay = self.__reload_delay
            self.data_load()

        # by date
        if time_now.tm_hour == 0 and time_now.tm_min == 0:
            date_key = time_now.tm_mon * 100 + time_now.tm_mday
            groups = self.__by_date_group_dict.get(date_key)
            users = self.__by_date_private_dict.get(date_key)
            if groups is not None:
                for grp in groups:
                    message = handlers.message.Message('group', '', 0, grp['user_id'], inter_msg=True)
                    message.group_id = grp['group_id']
                    message.message = message.raw_message = grp['message']
                    message.handle()
                    if message.can_call:
                        reply = message.reply
                    else:
                        reply = message.message
                    api.gocqhttp.send_group_msg(grp['group_id'], reply)
            if users is not None:
                for usr in users:
                    message = handlers.message.Message('private', 'friend', 0, usr['user_id'], inter_msg=True)
                    message.message = message.raw_message = usr['message']
                    message.handle()
                    if message.can_call:
                        reply = message.reply
                    else:
                        reply = message.message
                    api.gocqhttp.send_private_msg(usr['user_id'], reply)

        # by time
        time_key = time_now.tm_hour * 100 + time_now.tm_min
        groups = self.__by_time_group_dict.get(time_key)
        users = self.__by_time_private_dict.get(time_key)
        if groups is not None:
            for grp in groups:
                message = handlers.message.Message('group', '', 0, grp['user_id'], inter_msg=True)
                message.group_id = grp['group_id']
                message.message = message.raw_message = grp['message']
                message.handle()
                if message.can_call:
                    reply = message.reply
                else:
                    reply = message.message
                api.gocqhttp.send_group_msg(grp['group_id'], reply)
        if users is not None:
            for usr in users:
                message = handlers.message.Message('private', 'friend', 0, usr['user_id'], inter_msg=True)
                message.message = message.raw_message = usr['message']
                message.handle()
                if message.can_call:
                    reply = message.reply
                else:
                    reply = message.message
                api.gocqhttp.send_private_msg(usr['user_id'], reply)

        # commands
        cfg = haku.config.Config()
        prefix = cfg.get_index()
        for inter, comm in self.__commands_group_dict.items():
            for com in comm:
                com['delay'] -= 1
                if com['delay'] > 0:
                    continue
                com['delay'] = inter
                message = handlers.message.Message('group', '', 0, com['user_id'], inter_msg=True)
                message.group_id = com['group_id']
                message.message = message.raw_message = prefix + com['command']
                message.handle()
                message.reply_send()
        for inter, comm in self.__commands_private_dict.items():
            for com in comm:
                com['delay'] -= 1
                if com['delay'] > 0:
                    continue
                com['delay'] = inter
                message = handlers.message.Message('private', 'friend', 0, com['user_id'], inter_msg=True)
                message.message = message.raw_message = prefix + com['command']
                message.handle()
                message.reply_send()

    def commands_get(self, cmd_type: str, qid: int) -> list:
        """
        获取 commands 列表
        :param cmd_type: group/private
        :param qid: group_id/user_id
        :return: 列表
        """
        ans = []
        cfg = haku.config.Config()
        prefix = cfg.get_index()
        if cmd_type == 'group':
            for inter, cmd_list in self.__commands_group_dict.items():
                for cmd in cmd_list:
                    if cmd['group_id'] == qid:
                        ans.append({'user_id': cmd['user_id'], 'command': prefix+cmd['command'], 'interval': inter})
        if cmd_type == 'private':
            for inter, cmd_list in self.__commands_private_dict.items():
                for cmd in cmd_list:
                    if cmd['user_id'] == qid:
                        ans.append({'command': prefix+cmd['command'], 'interval': inter})
        return ans

    def commands_del(self, cmd_type: str, qid: int, index: int) -> bool:
        """
        删除指定的 command
        :param cmd_type: group/private
        :param qid: group_id/user_id
        :param index: 在 commands_get 获得的列表中的位置
        :return: 是否成功删除
        """
        if index <= 0:
            return False
        cmd = ''
        user_id = 0
        inter = 0
        with self.__commands_lock:
            if cmd_type == 'group':
                for intv, cmd_list in self.__commands_group_dict.items():
                    for i in range(len(cmd_list)):
                        if cmd_list[i]['group_id'] == qid:
                            index -= 1
                        if index == 0:
                            user_id = cmd_list[i]['user_id']
                            cmd = cmd_list[i]['command']
                            inter = intv
                            cmd_list.pop(i)
                            break
            elif cmd_type == 'private':
                for intv, cmd_list in self.__commands_private_dict.items():
                    for i in range(len(cmd_list)):
                        if cmd_list[i]['user_id'] == qid:
                            index -= 1
                        if index == 0:
                            cmd = cmd_list[i]['command']
                            inter = intv
                            cmd_list.pop(i)
                            break
        if index != 0:
            return False

        conn = data.sqlite.sqlite_open_db(self.__db_name)
        flag = True
        try:
            cur = conn.cursor()
            if cmd_type == 'group':
                cur.execute('DELETE FROM commands '
                            'WHERE type=? AND user_id=? AND group_id=? AND command=? AND interval=?',
                            (cmd_type, user_id, qid, cmd, inter))
            elif cmd_type == 'private':
                cur.execute('DELETE FROM commands '
                            'WHERE type=? AND user_id=? AND command=? AND interval=?',
                            (cmd_type, qid, cmd, inter))
            cur.close()
        except Exception as e:
            data.log.get_logger().exception(f'RuntimeError while delete from commands: {e}')
            flag = False
        data.sqlite.sqlite_close_db(conn)

        return flag

    def commands_add(self, cmd_type: str, user_id: int, group_id: int, cmd: str, interval: int) -> bool:
        """
        添加新的 command
        :param cmd_type: group/private
        :param user_id: qq id
        :param group_id: group id （cmd_type 为 private 时无效）
        :param cmd: 添加的 command
        :param interval: command 执行间隔时间秒
        :return: 是否成功添加
        """
        prefix = haku.config.Config().get_index()
        cmd = cmd.strip()
        if cmd_type not in ('group', 'private'):
            return False
        if isinstance(cmd, str) and len(cmd) < 2:
            return False
        if prefix != cmd[0]:
            return False
        cmd = cmd[1:]
        cmd_list = cmd.split()
        plugin = handlers.message.Plugin(cmd_list[0])
        code, flag, _ = plugin.test()
        if not code or not flag:
            return False

        flag = True
        conn = data.sqlite.sqlite_open_db(self.__db_name)
        try:
            cur = conn.cursor()
            new_dict = {'user_id': user_id, 'command': cmd, 'delay': interval}
            if cmd_type == 'group':
                new_dict['group_id'] = group_id
                if interval in self.__commands_group_dict.keys():
                    self.__commands_group_dict[interval].append(new_dict)
                else:
                    self.__commands_group_dict[interval] = [new_dict, ]
                sql = 'INSERT INTO commands(type, user_id, group_id, command, interval) VALUES(?, ?, ?, ?, ?)'
                cur.execute(sql, (cmd_type, user_id, group_id, cmd, interval))
            else:
                if interval in self.__commands_private_dict.keys():
                    self.__commands_private_dict[interval].append(new_dict)
                else:
                    self.__commands_private_dict[interval] = [new_dict, ]
                sql = 'INSERT INTO commands(type, user_id, command, interval) VALUES(?, ?, ?, ?)'
                cur.execute(sql, (cmd_type, user_id, cmd, interval))
            cur.close()
        except Exception as e:
            data.log.get_logger().exception(f'RuntimeError while insert into commands: {e}')
            flag = False
        data.sqlite.sqlite_close_db(conn)

        return flag

    def __schedule_get(self, edit_dict: dict, qid_name: str, qid: int) -> list:
        """
        以指定的键值对从指定的 dict 中获取列表 为了代码复用所以设置这个函数
        :param edit_dict: 指定的 dict
        :param qid_name: 键名 group_id/user_id
        :param qid: 键值
        :return: 列表
        """
        ans = []
        for key, values in edit_dict.items():
            for itm in values:
                if itm[qid_name] == qid:
                    ans.append({'key': key, 'message': itm['message'], 'user_id': itm['user_id']})
        return ans

    def schedule_get_by_time(self, type_name: str, qid: int) -> list:
        """
        获取时间定时消息 依赖 __schedule_get
        :param type_name: group/private
        :param qid: group_id/user_id
        :return: 列表
        """
        if type_name == 'group':
            ans = self.__schedule_get(self.__by_time_group_dict, 'group_id', qid)
            for itm in ans:
                key = itm['key']
                itm.pop('key')
                itm.update({'hour': key//100, 'minute': key%100})
            return ans
        elif type_name == 'private':
            ans = self.__schedule_get(self.__by_time_private_dict, 'user_id', qid)
            for itm in ans:
                key = itm['key']
                itm.pop('key')
                itm.update({'hour': key // 100, 'minute': key % 100})
            return ans
        else:
            return []

    def schedule_get_by_date(self, type_name: str, qid: int) -> list:
        """
        获取日期定时消息 依赖 __schedule_get
        :param type_name: group/private
        :param qid: group_id/user_id
        :return: 列表
        """
        if type_name == 'group':
            ans = self.__schedule_get(self.__by_date_group_dict, 'group_id', qid)
            for itm in ans:
                key = itm['key']
                itm.pop('key')
                itm.update({'month': key//100, 'day': key%100})
            return ans
        elif type_name == 'private':
            ans = self.__schedule_get(self.__by_date_private_dict, 'user_id', qid)
            for itm in ans:
                key = itm['key']
                itm.pop('key')
                itm.update({'month': key // 100, 'day': key % 100})
            return ans
        else:
            return []

    def __schedule_add(self, edit_dict: dict, dict_key: int, dict_value: dict, sql: str, sql_value: tuple) -> bool:
        """
        添加函数 指定 dict 的 key 和 value （向缓存添加）， 指定 sql 语句（向数据库添加）
        :param edit_dict: 指定的 dict
        :param dict_key: dict 的 key
        :param dict_value: dict 添加的 value
        :param sql: sql 语句
        :param sql_value: sql 语句动态插入需要的参数元组
        :return: 是否成功添加
        """
        conn = data.sqlite.sqlite_open_db(self.__db_name)
        flag = True
        try:
            if dict_key in edit_dict.keys():
                edit_dict[dict_key].append(dict_value)
            else:
                edit_dict[dict_key] = [dict_value, ]
            cur = conn.cursor()
            cur.execute(sql, sql_value)
            cur.close()
            conn.commit()
        except Exception as e:
            data.log.get_logger().exception(f'RuntimeError while insert into schedule: {e}')
            flag = False
        data.sqlite.sqlite_close_db(conn)
        return flag

    def schedule_add_by_time(self, type_name: str, user_id: int, group_id: int,
                             hour: int, minute: int, message: str) -> bool:
        """
        添加时间定时消息 依赖 __schedule_add
        :param type_name: group/private
        :param user_id: user id
        :param group_id: group id （type_name 为 group 时有效）
        :param hour: 小时
        :param minute: 分钟
        :param message: 消息
        :return: 是否添加成功
        """
        key = hour * 100 + minute
        if type_name == 'group':
            dict_value = {'user_id': user_id, 'group_id': group_id, 'message': message}
            sql = 'INSERT INTO bytime(type, user_id, group_id, hour, minute, message) VALUES(?, ?, ?, ?, ?, ?);'
            sql_value = (type_name, user_id, group_id, hour, minute, message)
            return self.__schedule_add(self.__by_time_group_dict, key, dict_value, sql, sql_value)
        elif type_name == 'private':
            dict_value = {'user_id': user_id, 'message': message}
            sql = 'INSERT INTO bytime(type, user_id, hour, minute, message) VALUES(?, ?, ?, ?, ?);'
            sql_value = (type_name, user_id, hour, minute, message)
            return self.__schedule_add(self.__by_time_private_dict, key, dict_value, sql, sql_value)

        return False

    def schedule_add_by_date(self, type_name: str, user_id: int, group_id: int,
                             month: int, day: int, message: str) -> bool:
        """
        添加日期定时消息 依赖 __schedule_add
        :param type_name: group/private
        :param user_id: user id
        :param group_id: group id （type_name 为 group 时有效）
        :param month: 月份
        :param day: 日
        :param message: 消息
        :return: 是否添加成功
        """
        key = month * 100 + day
        if type_name == 'group':
            dict_value = {'user_id': user_id, 'group_id': group_id, 'message': message}
            sql = 'INSERT INTO bydate(type, user_id, group_id, month, day, message) VALUES(?, ?, ?, ?, ?, ?);'
            sql_value = (type_name, user_id, group_id, month, day, message)
            return self.__schedule_add(self.__by_date_group_dict, key, dict_value, sql, sql_value)
        elif type_name == 'private':
            dict_value = {'user_id': user_id, 'message': message}
            sql = 'INSERT INTO bydate(type, user_id, month, day, message) VALUES(?, ?, ?, ?, ?);'
            sql_value = (type_name, user_id, month, day, message)
            return self.__schedule_add(self.__by_date_private_dict, key, dict_value, sql, sql_value)

        return False

    def __schedule_find_by_index(self, edit_dict: dict, qid_name: str, qid: int, index: int) -> (bool, int, dict):
        """
        根据 __schedule_list 列表中的位置，获取在实际 dict 中的位置和记录。假设实际位置为 pos ，则对应记录为 dict[key][pos]
        :param edit_dict: 指定 dict
        :param qid_name: group_id/user_id
        :param qid: 指定的 qid 值
        :param index: __schedule_list 列表中的位置
        :return: (是否找到, 实际位置, 记录)
        """
        ans_dict = {}
        real_index = 0
        if index <= 0:
            return False, real_index, ans_dict
        for key, values in edit_dict.items():
            for i in range(len(values)):
                if values[i][qid_name] == qid:
                    index -= 1
                if index == 0:
                    ans_dict = {'key': key,
                                'user_id': values[i]['user_id'],
                                'group_id': values[i].get('group_id'),
                                'message': values[i]['message']
                                }
                    real_index = i
                    break
        return index == 0, real_index, ans_dict

    def __schedule_del(self, edit_dict: dict, dict_key: int, list_index: int, sql: str, sql_value: tuple) -> bool:
        """
        删除指定 dict 中的指定记录，通过指定的 sql 语句和动态插入元组删除数据库中的记录
        :param edit_dict: 指定 dict
        :param dict_key: dict key
        :param list_index: key 对应的记录列表中，指定记录的位置
        :param sql: sql 语句
        :param sql_value: 动态插入元组
        :return: 是否成功删除
        """
        flag = True
        conn = data.sqlite.sqlite_open_db(self.__db_name)
        try:
            edit_dict[dict_key].pop(list_index)
            cur = conn.cursor()
            cur.execute(sql, sql_value)
            cur.close()
        except Exception as e:
            data.log.get_logger().exception(f'RuntimeError while delete lines from schedule: {e}')
            flag = False
        data.sqlite.sqlite_close_db(conn)
        return flag

    def schedule_del_by_time(self, type_name: str, qid: int, index: int) -> bool:
        """
        删除时间定时消息 依赖 __schedule_find_by_index 和 __schedule_del
        :param type_name: group/private
        :param qid: group_id/user_id
        :param index: __schedule_get 获得的列表中的位置
        :return: 是否删除成功
        """
        with self.__schedules_lock:
            if type_name == 'group':
                flag, real_index, value = self.__schedule_find_by_index(self.__by_time_group_dict, 'group_id', qid, index)
                if not flag:
                    return flag
                dict_key = value['key']
                sql = 'DELETE FROM bytime ' \
                      'WHERE type=? AND user_id=? AND group_id=? AND hour=? AND minute=? AND message=?;'
                sql_value = (type_name, value['user_id'], qid, dict_key//100, dict_key%100, value['message'])
                return self.__schedule_del(self.__by_time_group_dict, dict_key, real_index, sql, sql_value)
            elif type_name == 'private':
                flag, real_index, value = self.__schedule_find_by_index(self.__by_time_private_dict, 'user_id', qid, index)
                if not flag:
                    return flag
                dict_key = value['key']
                sql = 'DELETE FROM bytime WHERE type=? AND user_id=? AND hour=? AND minute=? AND message=?;'
                sql_value = (type_name, value['user_id'], dict_key//100, dict_key%100, value['message'])
                return self.__schedule_del(self.__by_time_private_dict, dict_key, real_index, sql, sql_value)

        return False

    def schedule_del_by_date(self, type_name: str, qid: int, index: int) -> bool:
        """
        删除日期定时消息 依赖 __schedule_find_by_index 和 __schedule_del
        :param type_name: group/private
        :param qid: group_id/user_id
        :param index: __schedule_get 获得的列表中的位置
        :return: 是否删除成功
        """
        with self.__schedules_lock:
            if type_name == 'group':
                flag, value = self.__schedule_find_by_index(self.__by_date_group_dict, 'group_id', qid, index)
                if not flag:
                    return flag
                dict_key = value['key']
                sql = 'DELETE FROM bydate ' \
                      'WHERE type=? AND user_id=? AND group_id=? AND month=? AND day=? AND message=?;'
                sql_value = (type_name, value['user_id'], qid, dict_key // 100, dict_key % 100, value['message'])
                return self.__schedule_del(self.__by_date_group_dict, dict_key, index, sql, sql_value)
            elif type_name == 'private':
                flag, value = self.__schedule_find_by_index(self.__by_date_private_dict, 'user_id', qid, index)
                if not flag:
                    return flag
                dict_key = value['key']
                sql = 'DELETE FROM bydate WHERE type=? AND user_id=? AND month=? AND day=? AND message=?;'
                sql_value = (type_name, value['user_id'], dict_key // 100, dict_key % 100, value['message'])
                return self.__schedule_del(self.__by_date_private_dict, dict_key, index, sql, sql_value)

        return False
