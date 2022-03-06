"""
Loongnix 包查询
"""
import gnupg
import requests
import time
import hashlib
import gzip
import lzma
import threading
import re

import data.log
import data.sqlite
from handlers.message import Message

myLogger = data.log.get_logger()
database = 'commands.loongnix.db'


def __fetch_files(url: str, md5: str) -> dict:
    """
    从 Package Release 的 url 获取软件包列表文件并验证 md5
    :param url: url
    :param md5: md5
    :return: Package 包含的软件包列表
    """
    res = requests.get(url, timeout=60)
    if res.status_code == 200:
        content = res.content
        h = hashlib.md5()
        h.update(content)
        if h.hexdigest() != md5:
            return {}

        profix = url[-3:]
        if profix == '.gz':
            content = gzip.decompress(content).decode('utf-8')
        elif profix == '.xz':
            content = lzma.decompress(content, lzma.FORMAT_XZ).decode('utf-8')

        content = content.split('\n\n')
        result = {}
        for con in content:
            con = con.split('\n')
            if len(con) < 2:
                continue
            for conp in range(len(con)-1, -1, -1):
                if con[conp][0] == ' ':
                    con[conp-1] = f"{con[conp-1]}\n{con[conp]}"
                    con.pop(conp)
            pkg = ''
            inf = {}
            for pcon in con:
                pcon = pcon.split(':')
                if len(pcon) < 2:
                    continue
                key = pcon[0].strip()
                value = pcon[1].strip()
                if key == 'Package':
                    pkg = value
                else:
                    inf.update({key: value})
            if pkg and inf:
                result.update({pkg: inf})

        return result
    return {}


def __fetch_lists(baseurl: str, pkgtree: dict) -> dict:
    """
    递归获取镜像中完整的软件包列表
    :param baseurl: 源地址
    :param pkgtree: Release 数据结构
    :return: 软件包信息字典
    """
    subpaths = pkgtree['subdirs']
    if subpaths:
        tfiles = {}
        for s in subpaths.keys():
            url = f"{baseurl}/{s}"
            tfiles.update(__fetch_lists(url, subpaths[s]))
        return tfiles
    else:
        url = f"{baseurl}/{pkgtree['package']}"
        md5 = pkgtree['md5']
        trys = 0
        tfiles = {}
        # 从 Package Release 获取软件包列表
        while not tfiles:
            tfiles = __fetch_files(url, md5)
            trys += 1
            if trys > 5:
                break
        return tfiles


def __fetch_pkgs(baseurl: str, distri: str):
    """
    从网络获取软件包列表并更新本地数据库
    :param baseurl: 镜像站地址
    :param distri: 发行版名称
    """
    # 获取 InRelease 和 Release.gpg
    res = requests.get(url=f'{baseurl}dists/{distri}/InRelease', timeout=60)
    if res.status_code == 200:
        releasetext = res.text
    else:
        myLogger.warning(f'Fetch InRelease failed: {res.status_code}')
        return
    res = requests.get(url=f'{baseurl}dists/{distri}/Release.gpg', timeout=60)
    if res.status_code == 200:
        gpgtext = res.text
    else:
        myLogger.warning(f'Fetch Release.gpg failed: {res.status_code}')
        return

    # gpg 验证
    gpgtext = gpgtext.replace('\n', '')
    gpgtext = gpgtext.replace('\r', '')
    gpg = gnupg.GPG()
    status = gpg.decrypt(releasetext, passphrase=gpgtext)

    outmsg = status.data.decode('utf-8')
    if len(outmsg) == 0:
        myLogger.warning('No Release file.')

    dictmsg = outmsg.split()
    ansdict = {}
    anskey = ''
    ansmsg = ''
    for s in dictmsg:
        if s[-1] == ':':
            if anskey != '':
                ansdict.update({anskey: ansmsg.lstrip()})
            anskey = s[:-1]
            ansmsg = ''
        else:
            ansmsg = f'{ansmsg} {s}'
    if anskey != '':
        ansdict.update({anskey: ansmsg.lstrip()})

    # print(ansdict)
    ansdict['Date'] = time.strptime(ansdict['Date'], '%a, %d %b %Y %H:%M:%S %Z')
    ansdict['Architectures'] = ansdict['Architectures'].split()
    ansdict['Components'] = ansdict['Components'].split()

    files = ansdict.get('MD5Sum')
    comp = ansdict.get('Components')
    if files is None or comp is None:
        myLogger.warning('Unsupported mirror.')
    files = files.split()
    if len(files) % 3 != 0:
        myLogger.warning('Corrupt Release file.')

    pkgtree = {
            'subdirs': {},
            'package': '',
        }
    for dirname in ansdict['Components']:
        pkgtree['subdirs'].update({dirname: {'subdirs': {}, 'package': '', 'md5': '', 'size': '', }})
    pat = 'Package.*'
    for i in range(2, len(files), 3):
        fpath = files[i].split('/')
        if fpath[0] not in comp:
            continue
        if not re.match(pat, fpath[-1]):
            continue
        lenth = len(fpath)-1
        subtree = pkgtree['subdirs'][fpath[0]]
        for j in range(1, lenth):
            if fpath[j] not in subtree['subdirs'].keys():
                subtree['subdirs'].update({fpath[j]: {'subdirs': {}, 'package': '', 'md5': '', 'size': '', }})
            subtree = subtree['subdirs'][fpath[j]]
        if subtree['package'] == '' or subtree['size'] > int(files[i - 1]):
            subtree['package'] = fpath[-1]
            subtree['size'] = int(files[i - 1])
            subtree['md5'] = files[i - 2]

    pkglist = __fetch_lists(f'{baseurl}dists/{distribution}', pkgtree)

    with data.sqlite.sqlite_open_db(database) as conn:
        cur = conn.cursor()
        try:
            cur.execute('CREATE TABLE IF NOT EXISTS packages'
                        '(Package VARCHAR(2048), Version VARCHAR(2048), '
                        'Architecture VARCHAR(2048), Description VARCHAR(4096), '
                        'PRIMARY KEY(Package, Version));')
            cur.execute('CREATE TABLE IF NOT EXISTS lastupdate(date DOUBLE);')
            cur.execute('DELETE FROM packages;')
            for key in pkglist.keys():
                pkg = pkglist[key]
                cur.execute('INSERT INTO packages VALUES(?, ?, ?, ?);', (key, pkg['Version'], pkg['Architecture'], pkg['Description']))
            cur.execute('DELETE FROM lastupdate;')
            cur.execute('INSERT INTO lastupdate VALUES(?)', (time.time(),))
        except:
            pass
        else:
            conn.commit()


baseUrl = 'http://pkg.loongnix.cn/loongnix/'
distribution = 'DaoXiangHu-testing'
# 更新线程和锁
updateThread = threading.Thread()
updateLock = threading.Lock()


def __search_pkgs(pkg: str) -> str:
    """
    在数据库中进行软件包查询，每小时更新一次数据库
    :param pkg: 包名
    :return: 格式化后的软件包列表字符串
    """
    global updateThread, updateLock

    # 上次获取软件包列表时间
    with data.sqlite.sqlite_open_db(database) as conn:
        cur = conn.cursor()
        try:
            ans = cur.execute('SELECT * FROM lastupdate')
            ans = ans.fetchall()
        except:
            ans = ()
    if len(ans) > 0:
        delta = time.time() - ans[0][0]
    else:
        delta = -1
    if delta > 60*3600 or delta < 0:
        # 在新线程中重新拉取软件包列表
        if updateLock.acquire(timeout=1):
            try:
                if not updateThread.is_alive():
                    updateThread = threading.Thread(target=__fetch_pkgs, args=(baseUrl, distribution))
                    updateThread.start()
            except:
                pass
            updateLock.release()
        if updateThread.is_alive():
            return 'Updating database.'

    # 在数据库中查询软件包
    with data.sqlite.sqlite_open_db(database) as conn:
        cur = conn.cursor()
        try:
            ans = cur.execute('SELECT * FROM packages WHERE Package LIKE ?', (f'{pkg}%',))
            pkgs = ans.fetchall()
        except:
            return 'Search ERROR.'
    cnt = 0
    if pkgs:
        ans = 'Search result(s):'
    else:
        ans = 'No result.'
    for pk in pkgs:
        cnt += 1
        # slen = min(128, len(pk[3]))
        ans += f"\n\nPackage: {pk[0]} {pk[1]}\nArchitecture: {pk[2]}"
        if len(pk[3]) > 256:
            ans += f"\n{pk[3][0:256]}..."
        else:
            ans += f"\n{pk[3]}"
        if cnt >= 5:
            break
    return ans


def run(message: Message) -> str:
    req = list(message.raw_message.strip().split(' ', 1))
    helpmsg = 'Loongnix 包查询'
    if len(req) > 1:
        keywords = req[1].strip()
        return __search_pkgs(keywords)

    time.sleep(10)
    return helpmsg


def bye():
    global updateThread, updateLock
    if updateLock.acquire(timeout=1):
        cnt = 6
        while updateThread.is_alive():
            cnt -= 1
            time.sleep(10)
            if cnt <= 0:
                break
