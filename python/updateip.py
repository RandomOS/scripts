#!/usr/bin/env python
# -*- coding: utf-8 -*-

import io
import gzip
import json
import time
import urllib2
import logging

logging.basicConfig(level=logging.DEBUG, format='%(name)s: %(message)s')
logger = logging.getLogger(__name__)

g_wan_ip = ""


def url_request(url, data=None, headers=None, proxy=None, timeout=10):
    """ url request """
    if not isinstance(headers, dict):
        headers = {
            'Accept': '*/*',
            'Accept-Encoding': 'identity',
            'Connection': 'close',
            'DNT': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.65',
        }

    request = urllib2.Request(url, data, headers)

    if proxy:
        request.set_proxy(proxy, 'http')

    try:
        response = urllib2.urlopen(request, timeout=timeout)
    except urllib2.HTTPError as e:
        logger.error('HTTP Error %s: %s %s', e.code, e.msg, url)
        return
    except urllib2.URLError as e:
        logger.error('URL Error: %s %s', e.reason, url)
        return
    except Exception as e:
        logger.error('Error: %s %s', e, url)
        return

    try:
        content = response.read()
    except Exception as e:
        logger.error('Error: %s', e)
        return
    finally:
        response.close()

    content_encoding = response.headers.get('Content-Encoding')
    if content_encoding == 'gzip':
        gz_data = io.BytesIO(content)
        gz = gzip.GzipFile(fileobj=gz_data)
        try:
            content = gz.read()
        except IOError as e:
            logger.error('IOError: %s', e)
        finally:
            gz.close()

    return content


def make_headers(request_headers):
    keywords = ('Accept', 'Accept-Encoding', 'Accept-Language', 'Content-Type', 'Connection', 'Cookie',
                'DNT', 'Origin', 'Referer', 'User-Agent', 'X-Prototype-Version', 'X-Requested-With')
    items = [item.strip() for item in request_headers.split('\n')]

    headers = {}
    for item in items:
        if item.find(':') == -1:
            continue
        idx = item.index(':')
        key = item[:idx]
        value = item[(idx + 1):]
        if key in keywords:
            headers[key] = value.strip()

    return headers


def get_wan_ip():
    url = 'http://httpbin.org/ip'
    content = url_request(url)
    try:
        content = json.loads(content)
    except (TypeError, ValueError):
        return
    return content['origin']


def post_to_dweet(thing, data):
    request_headers = """
    POST /dweet/for/test HTTP/1.1
    Host: beta.dweet.io
    Connection: keep-alive
    Accept: application/json
    Origin: https://beta.dweet.io
    User-Agent: Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.76 Safari/537.36
    Content-Type: application/json
    DNT: 1
    Accept-Encoding: gzip, deflate
    """
    data = json.dumps(data)
    headers = make_headers(request_headers)
    url = 'https://dweet.io/dweet/for/%s' % thing
    content = url_request(url, data, headers)
    if content:
        try:
            content = json.loads(content)
        except (TypeError, ValueError):
            return False
        if content['this'] == 'succeeded':
            return True
    return False


def main():
    global g_wan_ip
    interval = 300
    timestamp = 0
    while True:
        ip = get_wan_ip()
        if ip and (g_wan_ip != ip or int(time.time()) - timestamp > 24 * 60 * 60):
            g_wan_ip = ip
            timestamp = int(time.time())
            data = {
                'timestamp': timestamp,
                'ip': ip
            }
            for _ in xrange(3):
                succeeded = post_to_dweet('z6pmpwlz', data)
                if succeeded:
                    break
        time.sleep(interval)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print 'quit'
