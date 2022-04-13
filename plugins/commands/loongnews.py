
import requests
import time
import re

import api.gocqhttp
import data.log
import data.sqlite
from handlers.message import Message

"""
龙芯开源社区新闻订阅
"""

# 初始化时间戳
start_time = time.gmtime(time.time() + 8 * 3600)
last_day = [start_time.tm_year, start_time.tm_mon, start_time.tm_mday]
# last_day = [2022, 3, 21]

# 订阅列表
subset = set()

database = 'commands.loongnews.db'


def __get_page(url) -> str:
    """
    获取原始页面
    :param url: url
    :return: 页面代码
    """
    try:
        res = requests.get(url=url, timeout=5)
    except Exception as e:
        pass
    else:
        if res.status_code == 200:
            return res.text
    return ''


def __loongnix_cn_news() -> list:
    """
    获取当天 loongnix.cn 产品新闻和社区新闻
    :return: 新闻列表
    """
    baseurl = 'http://www.loongnix.cn'
    suburls = {
        # 'product': '/index.php/%E4%BA%A7%E5%93%81%E6%96%B0%E9%97%BB',
        # 'community': '/index.php/%E7%A4%BE%E5%8C%BA%E6%96%B0%E9%97%BB',
        'lbrowser': '/zh/api/lbrowser/lbrowser-news/',
        'loongnix': '/zh/loongnix/loongnix-news/',
        'java': '/zh/api/java/java-news/',
        'media': '/zh/api/media/media-news/',
    }

    hits = []
    news = []
    for url in suburls.values():
        context = __get_page(baseurl + url)
        for h in re.findall(r'<li>(.*?)</li>', context, flags=re.DOTALL):
            hits.append(h)
    for s in hits:
        msgs = re.findall(r'(\d+)[/|-](\d+)[/|-](\d+)(.*?)</a>', s, flags=re.DOTALL)
        for h in msgs:
            if len(h) == 4:
                yy = int(h[0])
                mm = int(h[1])
                dd = int(h[2])
                if yy != last_day[0] or mm != last_day[1] or dd != last_day[2]:
                    continue
                msg = f'[{h[0]}/{h[1]}/{h[2]}] ' + re.sub(r'<(.*?)>', '', h[3]).strip()
                links = re.findall(r'href="(.*?)"', h[3], flags=0)
                # print(h)
                for l in links:
                    if len(l) > 1 and l[0] == '/':
                        msg += f'\n{baseurl}{l}'
                    else:
                        msg += f'\n{l}'
                news.append(msg)
    return news


def __refresh_and_send():
    """
    更新新闻并推送新新闻
    """
    global last_day
    timenow = time.gmtime(time.time() + 8 * 3600)
    # 新一天删除前一天的新闻
    if timenow.tm_year != last_day[0] or timenow.tm_mon != last_day[1] or timenow.tm_mday != last_day[2]:
        db = data.sqlite.sqlite_open_db(database)
        cursor = db.cursor()
        cursor.execute('DELETE FROM news;')
        cursor.close()
        data.sqlite.sqlite_close_db(db)
        last_day = [timenow.tm_year, timenow.tm_mon, timenow.tm_mday]
    # 获取今日新闻并更新数据库 post_news 为之前未推送新闻
    news = __loongnix_cn_news()
    ans = '龙芯开源社区新闻：'
    post_news = []
    db = data.sqlite.sqlite_open_db(database)
    cursor = db.cursor()
    for s in news:
        cursor.execute('SELECT content FROM news WHERE content=?;', (s, ))
        if len(cursor.fetchall()) == 0:
            post_news.append(s)
            cursor.execute('INSERT INTO news(content) values(?)', (s, ))
    cursor.close()
    data.sqlite.sqlite_close_db(db)
    # print(post_news)
    # 推送未推送新闻
    if len(post_news) > 0:
        for i in range(len(post_news)):
            ans += f'\n{i}. {post_news[i]}'
        # print(ans)
        for uid in subset:
            if uid > 0:
                api.gocqhttp.send_private_msg(uid, ans)
            else:
                api.gocqhttp.send_group_msg(-uid, ans)


def config():
    global subset
    # 初始化数据库和订阅列表
    mydb = data.sqlite.sqlite_open_db(database)
    cursor = mydb.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS ids(id Long);')
    cursor.execute('CREATE TABLE IF NOT EXISTS news(content Text);')
    ids = cursor.execute('SELECT id FROM ids;')
    ids = ids.fetchall()
    for uid in ids:
        subset.add(uid[0])
    cursor.close()
    data.sqlite.sqlite_close_db(mydb)


def run(message: Message) -> str:
    global subset, last_day

    comm = message.message.split()
    # 发送指令
    if len(comm) > 1 and comm[1] == 'send':
        __refresh_and_send()
        return ''

    # 用户指令
    if message.message_type == 'private':
        uid = message.user_id
    elif message.message_type == 'group':
        uid = - message.group_id
    else:
        return ''

    # 订阅检查
    status = uid in subset
    ans = """龙芯开源社区新闻：
sub 订阅
unsub 取消订阅"""
    if status:
        ans += '\n汝已订阅'
    else:
        ans += '\n汝未订阅'
    if len(comm) > 1 and comm[1] in ['sub', 'unsub']:
        db = data.sqlite.sqlite_open_db(database)
        cursor = db.cursor()
        if comm[1] == 'sub' and not status:
            subset.add(uid)
            cursor.execute('INSERT INTO ids(id) values(?)', (uid, ))
        elif comm[1] == 'unsub' and status:
            subset.remove(uid)
            cursor.execute('DELETE FROM ids WHERE id=?', (uid, ))
        cursor.close()
        data.sqlite.sqlite_close_db(db)
        ans = '汝的操作成功执行'

    return ans


if __name__ == '__main__':
    for s in __loongnix_cn_news():
        print(s)
