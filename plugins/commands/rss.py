import time
import requests
import feedparser
from typing import Dict, List

import data.sqlite
import api.gocqhttp
from handlers.message import Message


__db_name = 'commands.rss.db'
__rss_group: Dict[str, List[int]] = {}
__rss_private: Dict[str, List[int]] = {}
__last_feed: Dict[str, str] = {}
__err_list: Dict[str, float] = {}
__last_sync: bool


def __send():
    """
    发生推送信息
    """
    for url, lst in __rss_group.items():
        msg = __request(url)
        if msg:
            for uid in lst:
                api.gocqhttp.send_group_msg(uid, msg)
    for url, lst in __rss_private.items():
        msg = __request(url)
        if msg:
            for uid in lst:
                api.gocqhttp.send_private_msg(uid, msg)
    # 错误列表
    tm_now = time.time()
    for url, tm in __err_list.items():
        if tm_now - tm > 1 * 24 *3600:
            msg = f'{url} 已经超过一天不能正常推送消息，请考虑删除它 (ᗜ˰ᗜ)'
            for uid in __rss_group.get(url, []):
                api.gocqhttp.send_group_msg(uid, msg)
            for uid in __rss_private.get(url, []):
                api.gocqhttp.send_private_msg(uid, msg)


def __request(url: str) -> str:
    """
    获取新推送 不能正常获取推送的加入 __err_list
    :param url: url
    :return: 推送信息
    """
    global __last_feed, __err_list
    tm_now = time.time()
    ans = []
    last_feed = False
    last_title = ''
    if url in __last_feed.keys():
        last_feed = True
        last_title = __last_feed[url]
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            content = feedparser.parse(res.text)
        else:
            return ''
        # 获取推送
        entries = content.get('entries')
        feed = content.get('feed')
        # 没有入口
        if entries is None or feed is None or len(entries) == 0:
            if url not in __err_list.keys():
                __err_list[url] = tm_now
            return ''
        elif url in __err_list.keys():
            # 可以正常推送，如果在列表中则删除
            __err_list.pop(url)
        # 新推送
        for row in entries:
            title = row['title']
            update_time = time.mktime(row['updated_parsed'])
            if last_feed and last_title == title:
                break
            # 十分钟以内可以接受
            if tm_now - update_time < 600.0:
                ans.append(f'{title}\n{row.get("author", "")}\n{row.get("link", "")}')
            else:
                break
        if len(ans) > 0:
            __last_feed[url] = entries[0]['title']
        msg = f'来自 {feed.get("title", "")}'
        for s in ans:
            msg += '\n' + s
        return msg
    except:
        if url not in __err_list.keys():
            __err_list[url] = tm_now
        return ''


def __db_exec(sql: str, sql_value: tuple) -> bool:
    conn = data.sqlite.sqlite_open_db(__db_name)
    try:
        cur = conn.cursor()
        cur.execute(sql, sql_value)
        cur.close()
    except:
        data.sqlite.sqlite_close_db(conn)
        return False
    data.sqlite.sqlite_close_db(conn)
    return True


def __add(msg_type: str, qid: int, url: str) -> bool:
    sql = 'INSERT INTO rss(type, id, url) VALUES(?, ?, ?);'
    sql_value = (msg_type, qid, url)
    if msg_type in ('group', 'private'):
        return __db_exec(sql, sql_value)
    else:
        return False


def __get(msg_type: str, qid: int) -> str:
    url_lst = []
    if msg_type == 'group':
        for url, lst in __rss_group.items():
            if qid in lst:
                url_lst.append(url)
    elif msg_type == 'private':
        for url, lst in __rss_private.items():
            if qid in lst:
                url_lst.append(url)
    else:
        return ''
    if url_lst:
        ans = '订阅列表：'
    else:
        ans = '小白这里没有你的记录诶'
    for i in range(len(url_lst)):
        ans += f'\n{i} {url_lst[i]}'
    return ans


def __del(msg_type: str, qid: int, index: int) -> bool:
    sql = 'DELETE FROM rss WHERE type=? AND id=? AND url=?;'
    if msg_type == 'group':
        for url, lst in __rss_group.items():
            if qid in lst:
                index -= 1
            if index == 0:
                lst.remove(qid)
                return __db_exec(sql, (msg_type, qid, url))
    elif msg_type == 'private':
        for url, lst in __rss_private.items():
            if qid in lst:
                index -= 1
            if index == 0:
                lst.remove(qid)
                return __db_exec(sql, (msg_type, qid, url))
    else:
        return False


def config():
    global __rss_private, __rss_group, __last_sync
    conn = data.sqlite.sqlite_open_db(__db_name)
    rss_group: Dict[str, List[int]] = {}
    rss_private: Dict[str, List[int]] = {}
    cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS rss(type text, id int, url text);')
    for row in cur.execute('SELECT type, id, url FROM rss;'):
        if row[0] == 'group':
            if row[1] in __rss_group.keys():
                rss_group[row[1]].append(row[2])
            else:
                rss_group[row[1]] = [row[2], ]
        elif row[0] == 'private':
            if row[1] in __rss_private.keys():
                rss_private[row[1]].append(row[2])
            else:
                rss_private[row[1]] = [row[2], ]
    cur.close()
    data.sqlite.sqlite_close_db(conn)
    __rss_private = rss_private
    __rss_group = rss_group
    __last_sync = time.time()


def run(message: Message):
    if time.time() - __last_sync > 50*60.0:
        config()
    help_msg = 'rss 推送\n' \
               '用法：\n' \
               '    rss list\n' \
               '    rss add <link>\n' \
               '    rss del <index>'

    msg_list = message.message.split()
    msg_len = len(msg_list)
    if message.message_type == 'group':
        qid = message.group_id
    elif message.message_type == 'private':
        qid = message.user_id
    else:
        return ''
    ans = help_msg
    if msg_len == 2:
        if msg_list[1] == 'list':
            return __get(message.message_type, qid)
        elif msg_list[1] == 'send':
            __send()
            return ''
    elif msg_len == 3:
        if msg_list[1] == 'add':
            if __add(message.message_type, qid, msg_list[2]):
                ans = f'添加成功 {msg_list[2]}'
            else:
                ans = f'添加失败 {msg_list[2]}'
        elif msg_list[1] == 'del':
            try:
                index = int(msg_list[2])
            except:
                ans = 'del 需要一个数字下标'
            else:
                if __del(message.message_type, qid, index):
                    ans = '删除成功'
                else:
                    ans = '删除失败'
    return ans
