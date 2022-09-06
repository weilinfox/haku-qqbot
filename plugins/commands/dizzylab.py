import os
import requests
import re

from handlers.message import Message


def search(key: str = 'Static World') -> dict:
    url = 'https://www.dizzylab.net/'
    params = {'s': key}
    res = requests.get(url=os.path.join(url, 'search/'), params=params)
    ans = {'l': [], "d": []}
    if res.status_code != 200:
        return ans

    blks = re.findall(r'<a href="(.+?)">.+? <img src="(.+?)".+?/>.+? <h1>(.+?)</h1>.+? </a>', res.text, re.M | re.S)
    for blk in blks:
        if re.match(r'/l/.+', blk[0]):
            ans['l'].append({'link': os.path.join(url, blk[0][1:] if blk[0][0] == '/' else blk[0]),
                             'cover': blk[1],
                             'title': blk[2]})
        elif re.match(r'/d/.+', blk[0]):
            ans['d'].append({'link': os.path.join(url, blk[0][1:] if blk[0][0] == '/' else blk[0]),
                             'cover': blk[1],
                             'title': blk[2]})
    return ans


def run(message: Message) -> str:
    help_msg = '小白会试着从 dizzylab 搜索 ´ ▽ ` )ﾉ'
    req = list(message.raw_message.split(' ', 1))
    ans = '好像啥也没有找到诶'
    if len(req) == 1:
        return help_msg

    key = req[1].strip()
    res = search(key)
    key = None
    if len(res['l']):
        key = res['l'][0]
    elif len(res['d']):
        key = res['d'][0]
    if not key:
        return ans

    ans = f'[CQ:share,url={key["link"]},title={key["title"]}]'
    return ans


if __name__ == "__main__":
    print(search())
