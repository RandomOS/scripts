#!/usr/bin/env python
# -*- coding: utf-8 -*-

import io
import os
import re
import sys
import gzip
import socket
import urllib2
import logging
import BaseHTTPServer
import SocketServer

logging.basicConfig(level=logging.DEBUG, format='%(name)s: %(message)s')
logger = logging.getLogger('google')

GOOGLE_IP = '203.116.165.138'


class GoogleFetch(object):

    """ GoogleFetch """

    def __init__(self):
        self.google_ip = GOOGLE_IP

    def fetch(self, path, headers):
        url = 'http://%s%s' % (self.google_ip, path)
        request = urllib2.Request(url)
        if headers['accept']:
            request.add_header('Accept', headers['accept'])
        if headers['accept_encoding']:
            request.add_header('Accept-Encoding', headers['accept_encoding'])
        if headers['accept_language']:
            request.add_header('Accept-Language', headers['accept_language'])
        if headers['if_modified_since']:
            request.add_header('If-Modified-Since', headers['if_modified_since'])
        if headers['user_agent']:
            request.add_header('User-Agent', headers['user_agent'])
        request.add_header('Connection', 'close')
        request.add_header('DNT', '1')

        try:
            response = urllib2.urlopen(request, timeout=30)
        except urllib2.HTTPError as e:
            return (e.code, None, None)
        except urllib2.URLError as e:
            logger.error('URL Error: %s %s', e.reason, url)
            return (500, None, None)
        except Exception as e:
            logger.error('Error: %s %s', e, url)
            return (500, None, None)

        content_type = response.headers.get('Content-Type')
        if not content_type:
            logger.error('can not find content-type in response header.')
            response.close()
            return (500, None, None)

        try:
            content = response.read()
        except Exception as e:
            logger.error('Error: %s', e)
            return (500, None, None)
        finally:
            response.close()

        content_encoding = response.headers.get('Content-Encoding')
        if content_encoding == 'gzip':
            gz_stream = io.BytesIO(content)
            gz_file = gzip.GzipFile(fileobj=gz_stream)
            try:
                content = gz_file.read()
            except IOError as e:
                logger.error('IOError: %s', e)
            finally:
                gz_file.close()

        if response.code == 200:
            text_types = ['text/html']
            for text_type in text_types:
                if content_type.startswith(text_type):
                    content = self.replace(content, headers['host'])
                    break

        response_headers = {
            'content_type': content_type,
            'cache_control': response.headers.get('Cache-Control'),
            'expires': response.headers.get('Expires'),
            'last_modified': response.headers.get('Last-Modified')
        }

        return response.code, response_headers, content

    def replace(self, content, host):
        content = content.replace('x.push(', '(')
        content = content.replace('!google.xjs', 'null')
        content = content.replace('google.log=', 'google.log=function(){};_log=')
        content = content.replace('="/images/', '="https://wen.lu/images/')
        content = content.replace('=\'/images/', '=\'https://wen.lu/images/')
        content = content.replace('url(/images/', 'url(https://wen.lu/images/')
        content = content.replace('//ssl.gstatic.com', 'https://www.glgoo.com/gstatic/ssl')
        content = re.sub(r'onmousedown=".+?" ', '', content)
        content = re.sub(r'(https?:)?//fonts\.googleapis\.com', 'https://fonts.lug.ustc.edu.cn', content)
        content = re.sub(r'(https?:)?//www\.google\.com', '//%s' % host, content)
        content = re.sub(r'(https?:)?//%s' % self.google_ip.replace('.', r'\.'), '//%s' % host, content)
        return content


class TimeoutHTTPRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):

    """
    Abandon request handling when client has not responded for a
    certain time. This raises a socket.timeout exception.
    """

    # Class-wide value for socket timeout
    timeout = 60
    protocol_version = 'HTTP/1.1'

    def setup(self):
        self.request.settimeout(self.timeout)
        BaseHTTPServer.BaseHTTPRequestHandler.setup(self)

    def process(self):
        """ process added """
        accept = self.headers.getheader('accept')
        accept_encoding = self.headers.getheader('accept-encoding')
        accept_language = self.headers.getheader('accept-language')
        host = self.headers.getheader('Host')
        if_modified_since = self.headers.getheader('if-modified-since')
        user_agent = self.headers.getheader('user-agent')

        headers = {
            'accept': accept,
            'accept_encoding': accept_encoding,
            'accept_language': accept_language,
            'host': host,
            'if_modified_since': if_modified_since,
            'user_agent': user_agent
        }

        google = GoogleFetch()
        code, response_headers, content = google.fetch(self.path, headers)
        if code == 200:
            self.send_response(200)
            content_type = response_headers['content_type']
            self.send_header('Content-Type', content_type)

            if response_headers['cache_control']:
                self.send_header('Cache-Control', response_headers['cache_control'])
            if response_headers['expires']:
                self.send_header('Expires', response_headers['expires'])
            if response_headers['last_modified']:
                self.send_header('Last-Modified', response_headers['last_modified'])

            gzip_enable = False
            if accept_encoding and accept_encoding.find('gzip') != -1:
                gzip_enable = True
            if gzip_enable and len(content) > 256:
                gzip_types = ('text', 'javascript', 'json', 'xml')
                for gzip_type in gzip_types:
                    if gzip_type in content_type:
                        content = self.gzip_encode(content)
                        self.send_header('Content-Encoding', 'gzip')
                        self.send_header('Vary', 'Accept-Encoding')
                        break

            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            if self.command != 'HEAD':
                self.wfile.write(content)
        else:
            self.send_error(code)

    def do_GET(self):
        """ do_GET added """
        self.process()

    def do_HEAD(self):
        """ do_HEAD added """
        self.process()

    def gzip_encode(self, content):
        """ gzip_encode added """
        gz_stream = io.BytesIO()
        gz_file = gzip.GzipFile(fileobj=gz_stream, mode='wb', compresslevel=6)
        gz_file.write(content)
        gz_file.close()
        return gz_stream.getvalue()

    def send_response(self, code, message=None):
        """ send_response overridden """
        self.log_request(code)
        if message is None:
            if code in self.responses:
                message = self.responses[code][0]
            else:
                message = ''
        self.wfile.write('%s %d %s\r\n' % (self.protocol_version, code, message))

        self.response_headers = {}
        self.send_header('Server', self.version_string())
        self.send_header('Date', self.date_time_string())
        if code >= 400:
            self.send_header('Connection', 'close')
            self.close_connection = 1
        else:
            self.send_header('Connection', 'keep-alive')
            self.close_connection = 0

    def send_header(self, keyword, value):
        """ send_header overridden """
        self.response_headers[keyword] = value

    def end_headers(self):
        """ end_headers overridden"""
        for key in sorted(self.response_headers.keys()):
            self.wfile.write('%s: %s\r\n' % (key, self.response_headers[key]))
        self.wfile.write('\r\n')

    def send_error(self, code, message=None):
        """ send_error overridden """
        try:
            short, _ = self.responses[code]
        except KeyError:
            short, _ = '???', '???'
        if message is None:
            message = short
        self.log_error('code %d, message %s', code, message)
        self.send_response(code, message)
        content = '%d, %s' % (code, message)
        content_type = 'text/plain; charset=utf-8'
        self.send_header('Content-Type', content_type)
        if code in (204, 304):
            self.send_header('Content-Length', '0')
        else:
            self.send_header('Content-Length', str(len(content)))
        self.end_headers()
        if self.command != 'HEAD' and code >= 200 and code not in (204, 304):
            self.wfile.write(content)

    def address_string(self):
        """ address_string overridden """
        host, port = self.client_address[:2]
        return host

    def version_string(self):
        """ version_string overridden """
        return 'Microsoft-IIS/8.5'


class ThreadedHTTPServer(SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer):

    """
    New features w/r to BaseHTTPServer.HTTPServer:
    - serves multiple requests simultaneously
    - catches socket.timeout and socket.error exceptions (raised from RequestHandler)
    """

    def __init__(self, *args):
        BaseHTTPServer.HTTPServer.__init__(self, *args)

    def process_request_thread(self, request, client_address):
        """
        Overrides SocketServer.ThreadingMixIn.process_request_thread
        in order to catch socket.timeout
        """
        try:
            self.finish_request(request, client_address)
            self.shutdown_request(request)
        except socket.timeout:
            sys.stderr.write('Timeout during processing of request from %s\n' % str(client_address))
        except socket.error, e:
            sys.stderr.write('%s during processing of request from %s\n' % (str(e), str(client_address)))
        except:
            self.handle_error(request, client_address)
            self.shutdown_request(request)


def main():
    if len(sys.argv) != 3:
        print '%s <ip> <port>' % os.path.basename(sys.argv[0])
        sys.exit()

    ip = sys.argv[1]
    port = int(sys.argv[2])
    httpd = ThreadedHTTPServer((ip, port), TimeoutHTTPRequestHandler)

    print 'Serving HTTP on %s port %d ...' % (ip, port)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print '^C received, shutting down server'


if __name__ == '__main__':
    main()
