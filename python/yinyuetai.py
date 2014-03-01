#!/usr/bin/env python
# -*- coding: utf-8 -*-

from gevent import monkey
monkey.patch_all()
import gevent
import gevent.pool
import requests
import os
import sys
import logging
import sqlite3

logging.basicConfig(level=logging.CRITICAL, format="%(message)s", filename="error.log", filemode="a")
logger = logging.getLogger("fetch")
logger.setLevel(logging.INFO)

sql = """
CREATE TABLE video(
    "id" INTEGER NOT NULL PRIMARY KEY,
    "hc" TEXT default NULL,
    "hd" TEXT default NULL,
    "he" TEXT default NULL
);
"""


def init_db():
    global sql
    if os.path.exists("yinyuetai.db"):
        conn = sqlite3.connect("yinyuetai.db")
    else:
        conn = sqlite3.connect("yinyuetai.db")
        conn.execute(sql)
    return conn


conn = init_db()
s = requests.Session()
count = 0
begin_id = 1
end_id = 100
total = end_id - begin_id
percent = -1


def fetch(video_id):
    global s, conn, count, total, percent
    url = "http://www.yinyuetai.com/api/info/get-video-urls"
    payload = {"json": "true", "videoId": video_id}
    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; rv:27.0) Gecko/20131201 Firefox/27.0"
    }

    count += 1
    if int(count * 100.0 / total) > percent:
        percent = int(count * 100.0 / total)
        sys.stdout.write("\r%d%%" % percent)

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
    except (requests.exceptions.HTTPError, AssertionError) as e:
        return

    try:
        result = r.json()
    except:
        return

    hc = result.get("hcVideoUrl")
    hd = result.get("hdVideoUrl")
    he = result.get("heVideoUrl")
    if hc:
        hc = hc.split('?')[0]
    if hd:
        hd = hd.split('?')[0]
    if he:
        he = he.split('?')[0]

    if hc or hd or he:
        try:
            conn.execute("insert into video values (?, ?, ?, ?)", (video_id, hc, hd, he))
            if count % 10000 == 0:
                conn.commit()
        except:
            pass


def timer(f):
    import sys
    import time
    if sys.platform[:3] == "win":
        timefunc = time.clock
    else:
        timefunc = time.time

    def wrapper(*args, **kargs):
        now = timefunc()
        try:
            return f(*args, **kargs)
        finally:
            sys.stdout.write("time delta: %.2fs\n" % (timefunc() - now))
    return wrapper


@timer
def main():
    global conn, begin_id, end_id
    pool = gevent.pool.Pool(10)
    for i in range(begin_id, end_id):
        pool.spawn(fetch, i)
    pool.join()
    conn.commit()
    conn.close()
    sys.stdout.write("\r100%\n")

if __name__ == '__main__':
    main()
