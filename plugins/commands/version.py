"""
获取版本号
"""
import requests

import haku.config

url: str


def config():
    global url
    cfg = haku.config.Config()
    url = f'http://{cfg.get_listen_host()}:{cfg.get_listen_port()}/version'


def run(message) -> str:
    try:
        resp = requests.get(url=url, timeout=5)
    except Exception as e:
        haku_bot_ver = f'获取版本号失败 {e}'
    else:
        if resp.status_code == 200:
            haku_bot_ver = resp.text
        else:
            haku_bot_ver = '获取版本号失败'

    return f'小白哦~\n{haku_bot_ver}\n' \
           f'Gitee: https://gitee.com/weilinfox/haku-qqbot/\n' \
           f'GitHub: https://github.com/weilinfox/haku-qqbot'
