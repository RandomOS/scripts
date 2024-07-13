#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import sys
import urllib2
import logging
import argparse
from functools import partial
from multiprocessing.dummy import Pool as ThreadPool

logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s] %(levelname)s [%(name)s:%(lineno)d] "%(message)s"')
logger = logging.getLogger('getproxy')


def get_page_content(url):
    """ get page content """
    request = urllib2.Request(url)
    request.add_header('Accept', 'text/html')
    request.add_header('Connection', 'close')
    request.add_header('DNT', '1')
    request.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 7.0; rv:27.0) Firefox/27.0')

    try:
        r = urllib2.urlopen(request, timeout=10)
    except Exception as e:
        logger.error('urlopen %s', url)
        return

    content_type = r.headers.get('Content-Type')
    if not content_type:
        r.close()
        return
    if content_type.find('text/html') == -1:
        r.close()
        return

    try:
        content = r.read()
    except Exception as e:
        logger.error('read %s', url)
        return
    finally:
        r.close()
    return content


def extract_proxy(content):
    """ extract proxy """
    proxy_li = []
    pattern = re.compile(r'<td>([\d.]+)</td>\s+<td>(\d+)</td>', re.I)
    match = pattern.findall(content)
    for item in match:
        ip, port = item
        proxy_li.append('%s:%s' % (ip, port))
    return proxy_li


def fetch_proxy_list():
    """ fetch proxy list """
    proxy_li = []
    url = 'http://www.xicidaili.com/wt/'
    content = get_page_content(url)
    if content is None:
        return []
    try:
        proxy = extract_proxy(content)
    except Exception as e:
        logger.error('extract_proxy failed')
        return []
    if proxy:
        proxy_li.extend(proxy)
    return proxy_li


def check_proxy(proxy, timeout):
    """ check proxy """
    request = urllib2.Request('http://www.baidu.com/')
    request.set_proxy(proxy, 'http')

    try:
        r = urllib2.urlopen(request, timeout=timeout)
    except Exception as e:
        return

    if r.code == 200:
        server = r.headers.getheader('server')
        if server and 'BWS' in server:
            return proxy


def check_proxy_list(proxy_li, timeout=5):
    """ check proxy list """
    pool = ThreadPool(20)
    result = pool.map(partial(check_proxy, timeout=timeout), proxy_li)
    result = [item for item in result if item]
    return result


def write_to_file(proxy_li, outfile):
    """ write proxy list to file """
    for proxy in proxy_li:
        outfile.write(proxy)
        outfile.write('\n')


def echo(content):
    """ echo content """
    print content


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument('-f', action='store_true', default=False,
                       dest='fetch', help='fetch proxy list from internet')
    group.add_argument('-i', metavar='in-file', type=argparse.FileType('rt'),
                       dest='infile', help='read proxy list from in-file')
    parser.add_argument('-c', action='store_true', default=False,
                        dest='check', help='verify proxy list, delete invalid proxy')
    parser.add_argument('-o', metavar='out-file', type=argparse.FileType('wt'),
                        dest='outfile', help='write proxy list to out-file')
    parser.add_argument('-v', action='version', version='%(prog)s 1.0')

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
    try:
        main()
    except KeyboardInterrupt:
        print 'quit'
