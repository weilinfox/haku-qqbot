"""
网抑云 基于一言
"""
import requests
import json

import data.log
from handlers.message import Message

myLogger = data.log.get_logger()


def run(message: Message) -> str:
    help_msg = '今天小白不高兴[CQ:face,id=107]'
    req = list(message.raw_message.split(' ', 1))
    if len(req) > 1:
        ans = help_msg
    else:
        try:
            resp = requests.get(url='https://v1.hitokoto.cn/', params={'c': 'j'})
            # resp = requests.get(url='http://api.heerdev.top:4995/nemusic/random', timeout=5)
            if resp.status_code == 200:
                rejson = json.loads(resp.text)
                # print(rejson)
                # ans = rejson['hitokoto']
                ans = rejson['text']
            else:
                ans = '好像返回了奇怪的东西: ' + str(resp.status_code)
        except Exception as e:
            myLogger.exception(f'RuntimeError {e}')
            ans = '啊嘞嘞好像出错了，一定是wyy炸了不关小白！'

    return ans
