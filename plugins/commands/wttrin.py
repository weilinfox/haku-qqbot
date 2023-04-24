import time

from handlers.message import Message


def run(message: Message) -> str:
    helpMsg = '一个访问 wttr.in 的小玩意'
    req = list(message.raw_message.split())
    for i in range(0, len(req)):
        req[i] = req[i].strip()
    if i == 0:
        ans = helpMsg
    else:
        ans = '[CQ:image,file=http://wttr.in/' + req[1] + '_tqp0_lang=en.png?hakuflag=' + str(int(time.time())) + ']'

    return ans
