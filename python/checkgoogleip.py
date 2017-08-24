#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import sys
import timeit
import urllib2
import logging
import argparse
from functools import partial
from multiprocessing.dummy import Pool as ThreadPool

logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s] %(levelname)s [%(name)s:%(lineno)d] "%(message)s"')
logger = logging.getLogger('check_google_ip')


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
    start = timeit.default_timer()
    protocol = 'https' if use_https else 'http'
    url = '%s://%s/' % (protocol, ip)
    request = urllib2.Request(url)
    request.get_method = lambda: 'HEAD'
    request.add_header('Accept', 'text/html,application/xhtml+xml')
    request.add_header('Connection', 'close')
    request.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.3; rv:30.0) Gecko/20140401 Firefox/30.0')

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

    end = timeit.default_timer()
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
    result = pool.map(partial(check_google_ip, use_https=opts.use_https), ip_list)
    result = [item for item in result if item]

    if opts.out_file:
        f = opts.out_file
    else:
        f = open('google.txt', 'w')

    result.sort(key=lambda x: x[1])
    for ip, duration in result:
        f.write('%-15s  %dms\n' % (ip, duration))
    f.close()
    print 'finish.'


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print 'quit'
