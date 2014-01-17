#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import sys
import string
import urllib2
import logging
import threading
import Queue
import argparse


class WorkThread(threading.Thread):

    """ WorkThread """

    def __init__(self, work_queue, result_queue):
        super(WorkThread, self).__init__()
        self.__work_queue = work_queue
        self.__result_queue = result_queue

    def run(self):
        while True:
            try:
                func, nkwargs, kwargs = self.__work_queue.get(False)
            except Queue.Empty:
                return
            try:
                ret = None
                ret = func(*nkwargs, **kwargs)
            except:
                pass
            if ret:
                self.__result_queue.put(ret)
            self.__work_queue.task_done()


class ThreadPool(object):

    """ ThreadPoolManager """

    def __init__(self, thread_num=10):
        self.__thread_num = thread_num
        self.__work_queue = Queue.Queue()
        self.__result_queue = Queue.Queue()
        self.__start = False
        self.__finish = False

    def start(self):
        self.__start = True
        for i in range(self.__thread_num):
            w = WorkThread(self.__work_queue, self.__result_queue)
            w.setDaemon(True)
            w.start()

    def add_job(self, func, *nkwargs, **kwargs):
        self.__work_queue.put((func, nkwargs, kwargs))

    def get_result(self):
        if not self.__finish:
            raise Exception("worker not finished.")
        li = []
        while not self.__result_queue.empty():
            ret = self.__result_queue.get(False)
            li.append(ret)
        return li

    def wait_all(self):
        if not self.__start:
            raise Exception("worker not started.")
        self.__work_queue.join()
        self.__finish = True


def get_page_content(url):
    """ get page content """
    request = urllib2.Request(url)
    request.add_header("Accept", "text/html")
    request.add_header("Connection", "close")
    request.add_header("DNT", "1")
    request.add_header("User-Agent", "Mozilla/5.0 "
                       "(Windows NT 7.0; rv:27.0) Firefox/27.0")

    try:
        response = urllib2.urlopen(request, timeout=5)
    except:
        logging.error("urlopen %s", url)
        return

    content_type = response.headers.get("Content-Type")
    if not content_type:
        response.close()
        return
    if content_type.find("text/html") == -1:
        response.close()
        return

    try:
        content = response.read()
    except:
        logging.error("read %s", url)
        return
    finally:
        response.close()

    return content


def extract_proxy(content):
    """extract proxy"""
    proxy_li = []

    pattern = re.compile('([a-zA-Z])="(\d)"')
    li = pattern.findall(content)

    letter = "".join([i[0] for i in li])
    number = "".join([i[1] for i in li])
    table = string.maketrans(letter, number)

    pattern = re.compile('<td>(.+)<SCRIPT.+?\(":"\+([a-zA-Z+]+)\)'
                         '</SCRIPT></td><td>HTTP</td>', re.I)
    li = pattern.findall(content)
    for item in li:
        ip = item[0]
        port = item[1].replace('+', '').translate(table)
        proxy_li.append("%s:%s" % (ip, port))

    return proxy_li


def fetch_proxy_list(page_count=1):
    """ fetch proxy list"""
    proxy_li = []
    for i in range(1, page_count + 1):
        url = "http://www.cnproxy.com/proxy%d.html" % i
        content = get_page_content(url)
        if content is None:
            continue
        try:
            proxy = extract_proxy(content)
        except:
            logging.error("extract_proxy failed")
            continue
        if proxy:
            proxy_li.extend(proxy)

    return proxy_li


def check_proxy(proxy, timeout):
    request = urllib2.Request("http://www.baidu.com/")
    request.set_proxy(proxy, "http")

    try:
        response = urllib2.urlopen(request, timeout=timeout)
    except:
        return

    if response.code == 200:
        return proxy


def check_proxy_list(proxy_li, timeout=5):
    """check proxy list"""
    threadpool = ThreadPool(20)

    for proxy in proxy_li:
        threadpool.add_job(check_proxy, proxy, timeout)

    threadpool.start()
    threadpool.wait_all()

    return threadpool.get_result()


def write_to_file(proxy_li, outfile):
    """write proxy list to file"""
    for proxy in proxy_li:
        outfile.write(proxy)
        outfile.write("\n")


def echo(content):
    """ echo content """
    print content


def main():
    parser = argparse.ArgumentParser(version="1.0")
    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument('-f', action="store_true", default=False,
                       dest="fetch", help="fetch proxy list from internet")
    group.add_argument('-i', metavar='in-file', type=argparse.FileType('rt'),
                       dest="infile", help="read proxy list from in-file")
    parser.add_argument("-c", action="store_true", default=False,
                        dest="check", help="verify proxy list, delete invalid proxy")
    parser.add_argument('-o', metavar='out-file', type=argparse.FileType('wt'),
                        dest="outfile", help="write proxy list to out-file")

    if not len(sys.argv) > 1:
        parser.print_help()
        exit()

    results = parser.parse_args()

    proxy_li = []
    if results.fetch:
        proxy_li = fetch_proxy_list(2)
    elif results.infile:
        proxy_li = [line.strip('\n') for line in results.infile]
        results.infile.close()

    if results.check:
        proxy_li = check_proxy_list(proxy_li)

    if results.outfile:
        write_to_file(proxy_li, results.outfile)
        results.outfile.close()
    else:
        map(echo, proxy_li)


if __name__ == '__main__':
    FORMAT = "%(levelname)s %(message)s"
    logging.basicConfig(level=logging.INFO, format=FORMAT)
    main()
