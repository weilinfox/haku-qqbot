"""
重载插件
"""
import requests
import time
import subprocess

import data.log
import haku.config
from handlers.message import Message, Plugin

__upgrade_flag = False


def run(message: Message) -> str:
    global __upgrade_flag
    msg_list = message.message.split()
    if len(msg_list) == 2 and msg_list[1] == 'upgrade':
        if __upgrade_flag:
            return 'Already upgrading'
        __upgrade_flag = True
        config = haku.config.Config()
        on_failure = True
        duration = time.time()
        trys = 0
        # git pull
        while on_failure:
            trys += 1
            code = subprocess.call(f'cd {config.get_root_path()} && git pull > /dev/null 2>&1', shell=True)
            if code == 0:
                on_failure = False
            else:
                time.sleep(5)
        __upgrade_flag = False
        # send reboot request
        url = f'http://{config.get_listen_host()}:{config.get_listen_port()}/stop'
        try:
            resp = requests.get(url, timeout=10)
        except:
            return 'Upgrade failed.'
        else:
            if resp.status_code != 200:
                return 'Upgrade failed.'
        duration = int(time.time() - duration)
        return f'Upgrade succeed.\nTried git pull {trys} times in {duration} seconds.'
    elif len(msg_list) != 1:
        return '升级 bot\n' \
               '用法：\n' \
               '    update\n' \
               '    update upgrade'
    data.log.get_logger().debug('Update plugin cache')
    try:
        plugin = Plugin()
        plugin.reload()
    except Exception as e:
        return f'Update plugin cache failed: {e}'
    return 'Update plugin cache success'
