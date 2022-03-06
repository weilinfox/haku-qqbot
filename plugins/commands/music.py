"""
网易云音乐
"""
import requests
import json

import data.log
import api.gocqhttp
from handlers.message import Message

# HOST = 'inuyasha.love'
# PORT = 8001
URL = 'http://inuyasha.love:8001/search'

myLogger = data.log.get_logger()


def run(message: Message) -> str:
    help_msg = '小白会试着从网易云搜索~'
    req = list(message.raw_message.split(' ', 1))
    ans = ''
    if len(req) > 1:
        req[1] = req[1].strip()
    if len(req) > 1 and len(req[1]) > 0:
        try:
            resp = requests.get(url=URL, params={'keywords': req[1]}, timeout=5)
        except Exception as e:
            myLogger.exception(f'RuntimeError {e}')
            return '啊嘞嘞好像出错了'
        else:
            if resp.status_code == 200:
                rejson = json.loads(resp.text)
                # print(resp.text)
                if rejson['result'].get('songs'):
                    mscid = rejson['result']['songs'][0]['id']
                    # mscname = rejson['result']['songs'][0]['name']
                    # ans = '[CQ:share,url=https://music.163.com/song/' + str(mscid) + '/,title=' + str(mscname) + ']'
                    if message.message_type == 'group':
                        api.gocqhttp.send_group_share_music(message.group_id, '163', mscid)
                    elif message.message_type == 'private':
                        api.gocqhttp.send_private_share_music(message.user_id, '163', mscid)
                else:
                    ans = '网易云里没有诶~'
            else:
                ans = '好像返回了奇怪的东西: ' + str(resp.status_code)
    else:
        ans = help_msg

    return ans
