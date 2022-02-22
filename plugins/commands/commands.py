
from handlers.message import Message
from handlers.schedule import Schedule


def run(message: Message):
    cmd = message.message.split()
    help_msg = '设置定时任务\n' \
               '用法：\n' \
               '    commands add <interval> <command>\n' \
               '    commands list\n' \
               '    commands del <index>'

    ans = help_msg
    cmd_len = len(cmd)
    schedule = Schedule()
    if message.is_group_message():
        qid = message.group_id
    elif message.is_private_message():
        qid = message.user_id
    else:
        return '只支持群和好友私聊'

    if cmd_len == 2:
        if cmd[1] == 'list':
            lst = schedule.commands_get(message.message_type, qid)
            is_empty = True
            ans = '指令列表'
            for i in range(len(lst)):
                ans += f'\n{i+1} {lst[i]["command"]} {lst[i]["interval"]} {lst[i].get("user_id", "")}'
                is_empty = False
            if is_empty:
                ans = '没有命令被设置'
    elif cmd_len == 3:
        if cmd[1] == 'del':
            try:
                index = int(cmd[2])
            except:
                ans = 'del 需要数字一个下标'
            else:
                if schedule.commands_del(message.message_type, qid, index):
                    ans = '删除成功'
                else:
                    ans = '删除失败'
    elif cmd_len >= 4:
        if cmd[1] == 'add':
            try:
                interval = abs(int(cmd[2]))
                if interval == 0:
                    interval = 1
            except:
                ans = 'add 需要一个数字间隔秒数'
            else:
                r_cmd = message.message.split(maxsplit=3)
                if schedule.commands_add(message.message_type, message.user_id, message.group_id, r_cmd[3], interval):
                    ans = f'添加成功 {interval}秒 {r_cmd[3]}'
                else:
                    ans = '添加失败'

    return ans
