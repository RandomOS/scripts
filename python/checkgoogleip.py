#!/usr/bin/env python
# -*- coding: utf-8 -*-

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


def check_google_ip(ip):
    """ get page content """
    url = 'https://%s/' % ip
    request = urllib2.Request(url)
    request.add_header('Accept', 'text/html,application/xhtml+xml')
    request.add_header('Connection', 'close')
    request.add_header('User-Agent', 'Mozilla/5.0 '
                       '(Windows NT 6.3; rv:30.0) Gecko/20140401 Firefox/30.0')

    # request.set_proxy('127.0.0.1:8087', 'http')

    try:
        response = urllib2.urlopen(request, timeout=10)
    except urllib2.HTTPError as e:
        logger.error('HTTP Error %s: %s %s', e.code, e.reason, url)
        return
    except urllib2.URLError as e:
        logger.error('URL Error: %s %s', e.reason, url)
        return
    except Exception as e:
        logger.error('Error: %s %s', e, url)
        return

    if response.code == 200:
        return ip


def main():
    ip_list = [line.strip('\n') for line in open('google_ip.txt')]

    threadpool = ThreadPool(20)

    for ip in ip_list:
        threadpool.add_job(check_google_ip, ip)

    threadpool.start()
    threadpool.wait_all()

    ret_li = threadpool.get_result()

    with open('available.txt', 'w') as f:
        for ip in ret_li:
            f.write(ip + '\n')
    print 'finish.'


if __name__ == '__main__':
    main()
