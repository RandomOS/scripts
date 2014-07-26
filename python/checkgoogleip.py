#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import time
import urllib2
import logging
import threading
import Queue

logging.basicConfig(level=logging.DEBUG, format='%(name)s: %(message)s')
logger = logging.getLogger(__name__)


class ThreadPoolException(Exception):

    """ Thread Pool Exception"""
    pass


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
                ret = func(*nkwargs, **kwargs)
            except:
                pass
            else:
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

    def wait_all(self):
        if not self.__start:
            raise ThreadPoolException('Worker not started.')
        self.__work_queue.join()
        self.__finish = True

    def get_result(self):
        if not self.__finish:
            raise ThreadPoolException('Worker not finished.')
        li = []
        while not self.__result_queue.empty():
            ret = self.__result_queue.get(False)
            li.append(ret)
        return li


def timefunc():
    """ time function """
    if os.name == 'nt':
        return time.clock()
    else:
        return time.time()


def get_google_ip_list():
    """ get google ip list """
    ip_data = [
        '1.179.248.132/187',
        '1.179.248.196/251',
        '1.179.248.4/59',
        '1.179.248.68/123',
        '1.179.249.132/187',
        '1.179.249.196/251',
        '1.179.249.4/59',
        '1.179.249.68/123',
        '1.179.250.132/187',
        '1.179.250.196/251',
        '1.179.250.4/59',
        '1.179.250.68/123',
        '1.179.251.140/187',
        '1.179.251.196/251',
        '1.179.251.4/59',
        '1.179.251.68/123',
        '1.179.252.132/187',
        '1.179.252.196/251',
        '1.179.252.68/123',
        '1.179.253.4/59',
        '1.179.253.76/123',
        '103.25.178.12/59',
        '103.25.178.4/6',
        '111.92.162.12/59',
        '111.92.162.4/6',
        '118.174.25.132/187',
        '118.174.25.196/251',
        '118.174.25.4/59',
        '118.174.25.68/123',
        '118.174.27.0/24',
        '121.78.74.68/123',
        '123.205.250.68/190',
        '123.205.251.68/123',
        '149.126.86.1/59',
        '163.28.116.1/59',
        '163.28.83.143/187',
        '173.194.0.0/16',
        '173.194.112.0/24',
        '178.45.251.4/123',
        '193.90.147.0/7',
        '193.90.147.12/59',
        '193.90.147.76/123',
        '197.199.253.1/59',
        '197.199.254.1/59',
        '202.39.143.1/123',
        '203.116.165.129/255',
        '203.117.34.132/187',
        '203.211.0.4/59',
        '203.66.124.129/251',
        '210.61.221.65/187',
        '213.240.44.5/27',
        '218.176.242.4/251',
        '218.189.25.129/187',
        '218.253.0.140/187',
        '218.253.0.76/92',
        '41.206.96.1/251',
        '41.84.159.12/30',
        '60.199.175.1/187',
        '61.219.131.193/251',
        '61.219.131.65/123',
        '62.197.198.193/251',
        '62.201.216.196/251',
        '84.235.77.1/251',
        '87.244.198.161/187',
        '88.159.13.196/251',
        '93.123.23.1/59'
    ]

    pattern = re.compile(r'(\d{1,3}\.\d{1,3}.\d{1,3})\.(\d{1,3})/(\d{1,3})')
    ip_group_list = pattern.findall('\n'.join(ip_data))

    ip_list = []
    for ip_group in ip_group_list:
        ip_prefix, start, end = ip_group
        for i in range(int(start), int(end) + 1):
            ip_list.append('%s.%d' % (ip_prefix, i))

    return ip_list


def check_google_ip(ip):
    """ check google ip """
    start = timefunc()
    url = 'https://%s/' % ip
    request = urllib2.Request(url)
    request.get_method = lambda: 'HEAD'
    request.add_header('Accept', 'text/html,application/xhtml+xml')
    request.add_header('Connection', 'close')
    request.add_header('User-Agent', 'Mozilla/5.0 '
                       '(Windows NT 6.3; rv:30.0) Gecko/20140401 Firefox/30.0')

    # request.set_proxy('127.0.0.1:8087', 'http')

    try:
        response = urllib2.urlopen(request, timeout=10)
    except urllib2.HTTPError as e:
        logger.error('HTTP Error %s: %s %s', e.code, e.msg, url)
        return
    except urllib2.URLError as e:
        logger.error('URL Error: %s %s', e.reason, url)
        return
    except Exception as e:
        logger.error('Error: %s %s', e, url)
        return

    end = timefunc()
    duration = int((end - start) * 1000)

    if response.code == 200:
        return (ip, duration)


def main():
    ip_list = get_google_ip_list()

    print 'check google ip list...'
    threadpool = ThreadPool(40)

    for ip in ip_list:
        threadpool.add_job(check_google_ip, ip)

    threadpool.start()
    threadpool.wait_all()

    ret_li = threadpool.get_result()

    with open('google.txt', 'w') as f:
        ret_li.sort(key=lambda x: x[1])
        for ip, duration in ret_li:
            f.write('%-15s  %dms\n' % (ip, duration))
    print 'finish.'


if __name__ == '__main__':
    main()
