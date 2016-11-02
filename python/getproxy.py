#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import sys
import urllib2
import logging
import threading
import Queue
import argparse

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s %(message)s')


class ThreadPoolException(Exception):

    """ Thread Pool Exception """
    pass


class WorkThread(threading.Thread):

    """ WorkThread """

    def __init__(self, work_queue, result_queue):
        super(WorkThread, self).__init__()
        self.__work_queue = work_queue
        self.__result_queue = result_queue

    def run(self):
        while True:
            content = self.__work_queue.get()
            if isinstance(content, str) and content == 'quit':
                break
            try:
                func, args, kwargs = content
                ret = func(*args, **kwargs)
            except:
                pass
            else:
                if ret:
                    self.__result_queue.put(ret)
            finally:
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
        for _ in range(self.__thread_num):
            worker = WorkThread(self.__work_queue, self.__result_queue)
            worker.setDaemon(True)
            worker.start()

    def add(self, func, *args, **kwargs):
        self.__work_queue.put((func, args, kwargs))

    def join(self):
        if not self.__start:
            raise ThreadPoolException('Worker not started')
        self.__work_queue.join()
        self.__finish = True

    def close(self):
        if not self.__finish:
            raise ThreadPoolException('Worker not finished')
        for _ in xrange(self.__thread_num):
            self.__work_queue.put('quit')

    def get_result(self):
        if not self.__finish:
            raise ThreadPoolException('Worker not finished')
        results = []
        while not self.__result_queue.empty():
            ret = self.__result_queue.get()
            results.append(ret)
        return results


def get_page_content(url):
    """ get page content """
    request = urllib2.Request(url)
    request.add_header('Accept', 'text/html')
    request.add_header('Connection', 'close')
    request.add_header('DNT', '1')
    request.add_header('User-Agent', 'Mozilla/5.0 '
                       '(Windows NT 7.0; rv:27.0) Firefox/27.0')

    try:
        response = urllib2.urlopen(request, timeout=10)
    except:
        logging.error('urlopen %s', url)
        return

    content_type = response.headers.get('Content-Type')
    if not content_type:
        response.close()
        return
    if content_type.find('text/html') == -1:
        response.close()
        return

    try:
        content = response.read()
    except:
        logging.error('read %s', url)
        return
    finally:
        response.close()

    return content


def extract_proxy(content):
    """ extract proxy """
    proxy_li = []
    pattern = re.compile(r'<tr><td>([\d.]+)</td><td>(\d+)</td>', re.I)
    match = pattern.findall(content)
    for item in match:
        ip, port = item
        proxy_li.append('%s:%s' % (ip, port))

    return proxy_li


def fetch_proxy_list():
    """ fetch proxy list """
    proxy_li = []
    url = 'https://free-proxy-list.net/'
    content = get_page_content(url)
    if content is None:
        return []
    try:
        proxy = extract_proxy(content)
    except:
        logging.error('extract_proxy failed')
        return []
    if proxy:
        proxy_li.extend(proxy)

    return proxy_li


def check_proxy(proxy, timeout):
    """ check proxy """
    request = urllib2.Request('http://www.baidu.com/')
    request.set_proxy(proxy, 'http')

    try:
        response = urllib2.urlopen(request, timeout=timeout)
    except:
        return

    if response.code == 200:
        server = response.headers.getheader('server')
        if server and 'BWS' in server:
            return proxy


def check_proxy_list(proxy_li, timeout=5):
    """ check proxy list """
    pool = ThreadPool(20)

    for proxy in proxy_li:
        pool.add(check_proxy, proxy, timeout)

    pool.start()
    pool.join()
    pool.close()

    return pool.get_result()


def write_to_file(proxy_li, outfile):
    """ write proxy list to file """
    for proxy in proxy_li:
        outfile.write(proxy)
        outfile.write('\n')


def echo(content):
    """ echo content """
    print content


def main():
    parser = argparse.ArgumentParser(version='1.0')
    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument('-f', action='store_true', default=False,
                       dest='fetch', help='fetch proxy list from internet')
    group.add_argument('-i', metavar='in-file', type=argparse.FileType('rt'),
                       dest='infile', help='read proxy list from in-file')
    parser.add_argument('-c', action='store_true', default=False,
                        dest='check', help='verify proxy list, delete invalid proxy')
    parser.add_argument('-o', metavar='out-file', type=argparse.FileType('wt'),
                        dest='outfile', help='write proxy list to out-file')

    if not len(sys.argv) > 1:
        parser.print_help()
        exit()

    opts = parser.parse_args()

    proxy_li = []
    if opts.fetch:
        proxy_li = fetch_proxy_list()
    elif opts.infile:
        proxy_li = [line.strip('\n') for line in opts.infile]
        opts.infile.close()

    if opts.check:
        proxy_li = check_proxy_list(proxy_li)

    if opts.outfile:
        write_to_file(proxy_li, opts.outfile)
        opts.outfile.close()
    else:
        map(echo, proxy_li)


if __name__ == '__main__':
    main()
