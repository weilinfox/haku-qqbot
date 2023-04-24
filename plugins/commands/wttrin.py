
from handlers.message import Message


def run(message: Message) -> str:
    help_msg = '一个访问 wttr.in 的小玩意'
    req = list(message.raw_message.split())
    for i in range(0, len(req)):
        req[i] = req[i].strip()
    if i == 0:
        ans = help_msg
    else:
        ans = '[CQ:image,file=http://wttr.in/' + req[1] + '_tqp0_lang=en.png,cache=0]'

    return ans
