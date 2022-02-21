
from handlers.message import Message
from handlers.schedule import Schedule


def run(message: Message):
    cmd = message.message.split()
    help_msg = '设置定时任务\n' \
               '用法：\n' \
               '    schedules add time <hhmm> <message>\n' \
               '    schedules add date <MMdd> <message>\n' \
               '    schedules list time\n' \
               '    schedules list date\n' \
               '    schedules del time <index>\n' \
               '    schedules del date <index>'

    ans = help_msg
    cmd_len = len(cmd)
    schedule = Schedule()
    if message.is_group_message():
        qid = message.group_id
    elif message.is_private_message():
        qid = message.user_id
    else:
        return '只支持群和好友私聊'

    if cmd_len == 3:
        if cmd[1] == 'list':
            is_empty = True
            ans = '指令列表'
            if cmd[2] == 'time':
                lst = schedule.schedule_get_by_time(message.message_type, qid)
                for i in range(len(lst)):
                    ans += f'\n{i + 1} {lst[i]["message"]} {lst[i]["hour"]}:{lst[i]["minute"]} {lst[i]["user_id"]}'
                    is_empty = False
                if is_empty:
                    ans = '没有命令被设置'
            elif cmd[2] == 'date':
                lst = schedule.schedule_get_by_date(message.message_type, qid)
                for i in range(len(lst)):
                    ans += f'\n{i + 1} {lst[i]["message"]} {lst[i]["month"]}/{lst[i]["day"]} {lst[i]["user_id"]}'
                    is_empty = False
                if is_empty:
                    ans = '没有命令被设置'
    elif cmd_len == 4:
        if cmd[1] == 'del':
            try:
                index = int(cmd[3])
            except:
                ans = 'del 需要数字一个下标'
            else:
                if cmd[2] == 'time':
                    if schedule.schedule_del_by_time(message.message_type, qid, index):
                        ans = '删除成功'
                    else:
                        ans = '删除失败'
                elif cmd[2] == 'date':
                    if schedule.schedule_del_by_date(message.message_type, qid, index):
                        ans = '删除成功'
                    else:
                        ans = '删除失败'
    elif cmd_len >= 5:
        if cmd[1] == 'add':
            try:
                tag = int(cmd[3])
            except:
                ans = '时间/日期应为四位数字（允许前导零）'
            else:
                r_cmd = message.message.split(maxsplit=4)
                if cmd[2] == 'time':
                    if schedule.schedule_add_by_time(message.message_type, message.user_id, message.group_id,
                                                     tag//100, tag % 100, r_cmd[4]):
                        ans = f'添加成功 {r_cmd[4]}'
                    else:
                        ans = '添加失败'
                elif cmd[2] == 'date':
                    if schedule.schedule_add_by_date(message.message_type, message.user_id, message.group_id,
                                                     tag//100, tag % 100, r_cmd[4]):
                        ans = f'添加成功 {r_cmd[4]}'
                    else:
                        ans = '添加失败'
    return ans
