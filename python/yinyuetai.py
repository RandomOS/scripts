#!/usr/bin/env python
# -*- coding: utf-8 -*-

from gevent import monkey
monkey.patch_all()
import gevent
import gevent.pool
import requests
import os
import re
import sys
import time
import logging
import sqlite3

logging.basicConfig(level=logging.CRITICAL, format='%(message)s', filename='miss.log', filemode='a')
logger = logging.getLogger('fetch')
logger.setLevel(logging.INFO)

g_sql = """
CREATE TABLE video (
    id INTEGER NOT NULL PRIMARY KEY,
    hc TEXT default NULL,
    hd TEXT default NULL,
    he TEXT default NULL
);
"""

g_count = 0
g_begin_id = 1
g_end_id = 100
g_total = g_end_id + 1 - g_begin_id
g_percent = -1
g_list = []

s = requests.Session()


def init():
    global g_sql, g_begin_id, g_end_id, g_total
    if os.path.exists('yinyuetai.db'):
        conn = sqlite3.connect('yinyuetai.db')
        query = conn.execute('select max(id) from video')
        max_id = query.fetchone()[0]
        g_begin_id = max(g_begin_id, max_id + 1)
        if g_begin_id < g_end_id + 1:
            g_total = g_end_id + 1 - g_begin_id
        else:
            sys.stdout.write('exit.\n')
            sys.exit()
    else:
        conn = sqlite3.connect('yinyuetai.db')
        conn.execute(g_sql)
    return conn


def fetch(video_id):
    global s, g_conn, g_count, g_total, g_percent, g_list
    url = 'http://www.yinyuetai.com/api/info/get-video-urls'
    payload = {'videoId': video_id}
    headers = {
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.2; rv:29.0) Gecko/20140101 Firefox/29.0'
    }

    g_count += 1
    if int(g_count * 100.0 / g_total) > g_percent:
        g_percent = int(g_count * 100.0 / g_total)
        sys.stdout.write('\r%d%%' % g_percent)

    try:
        r = s.get(url, headers=headers, params=payload, timeout=10)
    except requests.exceptions.Timeout:
        logger.info(video_id)
        return
    except:
        logger.warn(video_id)
        return

    try:
        r.raise_for_status()
    except requests.exceptions.HTTPError:
        return

    try:
        result = r.json()
    except:
        return

    hc = result.get('hcVideoUrl')
    hd = result.get('hdVideoUrl')
    he = result.get('heVideoUrl')
    if hc:
        hc = hc.split('?')[0]
    if hd:
        hd = hd.split('?')[0]
    if he:
        he = he.split('?')[0]

    if hc or hd or he:
        g_list.append((video_id, hc, hd, he))

    if g_count % 1000 == 0:
        g_conn.executemany('insert into video values (?, ?, ?, ?)', g_list)
        g_conn.commit()
        g_list = []


def finish():
    global g_conn, g_list
    if g_list:
        g_conn.executemany('insert into video values (?, ?, ?, ?)', g_list)
        g_conn.commit()
    g_conn.close()
    sys.stdout.write('\r100%\n')


def timer(f):
    if sys.platform[:3] == 'win':
        timefunc = time.clock
    else:
        timefunc = time.time

    def wrapper(*args, **kargs):
        now = timefunc()
        try:
            return f(*args, **kargs)
        finally:
            sys.stdout.write('time delta: %.2fs\n' % (timefunc() - now))
    return wrapper


def get_lastest_id():
    global s, g_end_id
    try:
        url = 'http://mv.yinyuetai.com/all?sort=pubdate'
        r = s.get(url, timeout=10)
        html = r.content
        regex_str = 'http:\/\/v.yinyuetai.com\/video\/(\d+)'
        pattern = re.compile(regex_str)
        lastest_id = int(max(pattern.findall(html)))
    except:
        sys.stdout.write('get lastest id failed!\n')
        return g_end_id
    return lastest_id


def collect_miss():
    global g_conn, g_count, g_total, g_list
    video_id_li = [line.strip('\n') for line in open('miss.log')]
    g_conn = sqlite3.connect('yinyuetai.db')
    g_count = 0
    g_total = len(video_id_li)
    for video_id in video_id_li:
        fetch(video_id)

    if g_list:
        g_conn.executemany('insert into video values (?, ?, ?, ?)', g_list)
        g_conn.commit()
    g_conn.close()
    sys.stdout.write('\r100%\n')


@timer
def main():
    global g_conn, g_begin_id, g_end_id
    pool = gevent.pool.Pool(10)
    for i in range(g_begin_id, g_end_id + 1):
        pool.spawn(fetch, i)
    pool.join()
    finish()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        collect_miss()
    else:
        g_end_id = get_lastest_id()
        g_conn = init()
        main()
