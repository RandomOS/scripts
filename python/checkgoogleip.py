#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
import time
import urllib2
import logging
import threading
import Queue
import argparse

logging.basicConfig(level=logging.DEBUG, format='%(name)s: %(message)s')
logger = logging.getLogger('check_google_ip')


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
            func, args, kwargs = self.__work_queue.get()
            try:
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
            w = WorkThread(self.__work_queue, self.__result_queue)
            w.setDaemon(True)
            w.start()

    def add(self, func, *args, **kwargs):
        self.__work_queue.put((func, args, kwargs))

    def join(self):
        if not self.__start:
            raise ThreadPoolException('Worker not started')
        self.__work_queue.join()
        self.__finish = True

    def get_result(self):
        if not self.__finish:
            raise ThreadPoolException('Worker not finished')
        results = []
        while not self.__result_queue.empty():
            ret = self.__result_queue.get()
            results.append(ret)
        return results


def timefunc():
    """ time function """
    if os.name == 'nt':
        return time.clock()
    else:
        return time.time()


def get_google_ip_list(ip_data):
    """ get google ip list """
    pattern = re.compile(r'^\d{1,3}\.\d{1,3}.\d{1,3}\.\d{1,3}$', re.M)
    ip_list = pattern.findall(ip_data)

    pattern = re.compile(r'^(\d{1,3}\.\d{1,3}.\d{1,3})\.(\d{1,3})-(\d{1,3})$', re.M)
    ip_group_list = pattern.findall(ip_data)

    for ip_group in ip_group_list:
        ip_prefix, start, end = ip_group
        for i in range(int(start), int(end) + 1):
            ip_list.append('%s.%d' % (ip_prefix, i))
    return set(ip_list)


def check_google_ip(ip, use_https):
    """ check google ip """
    start = timefunc()
    protocol = 'https' if use_https else 'http'
    url = '%s://%s/' % (protocol, ip)
    request = urllib2.Request(url)
    request.get_method = lambda: 'HEAD'
    request.add_header('Accept', 'text/html,application/xhtml+xml')
    request.add_header('Connection', 'close')
    request.add_header('User-Agent', 'Mozilla/5.0 '
                       '(Windows NT 6.3; rv:30.0) Gecko/20140401 Firefox/30.0')

    # request.set_proxy('127.0.0.1:8888', 'http')

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
        if response.headers.getheader('server') == 'gws':
            return (ip, duration)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', metavar='in-file', type=argparse.FileType('rt'),
                        dest='in_file', required=True, help='read ip list from in-file')
    parser.add_argument('-o', metavar='out-file', type=argparse.FileType('wt'),
                        dest='out_file', help='write google ip to out-file')
    parser.add_argument('--use-https', action='store_true', default=False,
                        dest='use_https', help='use https protocol to check ip')

    if not len(sys.argv) > 1:
        parser.print_help()
        exit()

    opts = parser.parse_args()

    if opts.in_file:
        ip_data = opts.in_file.read()
        opts.in_file.close()

    ip_list = get_google_ip_list(ip_data)

    print 'check google ip list...'
    pool = ThreadPool(40)

    for ip in ip_list:
        pool.add(check_google_ip, ip, opts.use_https)

    pool.start()
    pool.join()

    ret_li = pool.get_result()

    if opts.out_file:
        f = opts.out_file
    else:
        f = open('google.txt', 'w')

    ret_li.sort(key=lambda x: x[1])
    for ip, duration in ret_li:
        f.write('%-15s  %dms\n' % (ip, duration))
    f.close()
    print 'finish.'


if __name__ == '__main__':
    main()
