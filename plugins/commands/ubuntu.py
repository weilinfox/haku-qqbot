"""
Ubuntu 包查询
"""

import requests
import re

from handlers.message import Message


def __search_ubuntu(keywords):
    baseurl = 'https://packages.ubuntu.com'
    searchurl = '/search'
    params = {
        'suite': 'all',
        'section': 'all',
        'arch': 'any',
        'searchon': 'names',
        'keywords': keywords,
    }

    try:
        res = requests.get(url=baseurl+searchurl, params=params, timeout=20)
    except requests.exceptions.ReadTimeout:
        return 'Search timeout.'

    if res.status_code == 200:
        restexts = res.text.split()
        restext = ''
        for s in restexts:
            restext += ' ' + s

        search_res = {
            'package': '',
            'links': [],
        }

        hits = re.findall(r'<h3>.*?</ul>', restext, flags=0)
        if len(hits) > 0:
            hits = hits[0]
            name = re.findall(r'<h3>(.*?)</h3>', hits, flags=0)
            if len(name) > 0:
                search_res['package'] = name[0]
            links = re.findall(r'<li.*?</li>', hits, flags=0)
            for ln in links:
                href = re.findall(r'href="(.*?)</a>', ln, flags=0)
                if len(href) > 0:
                    href = href[0]
                    ln = ln.split(href, 1)[1][4:-5]
                    ln = ln.split('<br>', 1)
                    des = ln[0].strip()
                    ver = ln[1].strip()
                    dis = href.split('">', 1)
                    href = dis[0].strip()
                    dis = dis[1].strip()
                    inhtmls = re.findall(r'<.*?>', ver, flags=0)
                    for s in inhtmls:
                        ver = ver.replace(s, '')
                    inhtmls = re.findall(r'<.*?>', des, flags=0)
                    for s in inhtmls:
                        des = des.replace(s, '')
                    search_res['links'].append({
                        'distribution': dis,
                        'link': baseurl + href,
                        'description': des,
                        'version': ver,
                    })
            result = search_res['package']
            for ln in search_res['links']:
                result += f"\n{ln['distribution']}:\n{ln['description']}\n{ln['version']}\n{ln['link']}"
            return result
        else:
            return 'No search result.'
    else:
        return 'Cannot connect ubuntu.com'


def run(message: Message) -> str:
    req = list(message.raw_message.strip().split(' ', 1))
    help_msg = 'Ubuntu 包查询'
    if len(req) > 1:
        keywords = req[1].strip()
        return __search_ubuntu(keywords)

    return help_msg
