#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import socket
import struct
import hashlib
import logging
import optparse
import threading
from itertools import cycle, izip

logging.basicConfig(level=logging.DEBUG, format='[%(name)s:%(lineno)03d] %(message)s')
logger = logging.getLogger('pytunnel')

TAG = 128


def encrypt(value, key):
    result = ''.join(chr(ord(c) ^ ord(k)) for c, k in izip(value, cycle(key)))
    return result


def decrypt(value, key):
    return encrypt(value, key)


def wraptlv(tag, value):
    tag = struct.pack('B', tag)
    length = len(value)
    length = struct.pack('!H', length)
    data = tag + length + value
    return data


def recvtlv(sock):
    data = sock.recv(1)
    if not data:
        return data
    tag = struct.unpack('B', data)[0]
    if tag != TAG:
        return ''
    data = sock.recv(2)
    if not data:
        return data
    length = struct.unpack('!H', data)[0]
    data = ''
    size = length
    while size > 0:
        buf = sock.recv(size)
        data += buf
        size = length - len(data)
    return data


class SendEncrypt(threading.Thread):

    def __init__(self, source_sock, target_sock, key):
        super(SendEncrypt, self).__init__()
        self.source_sock = source_sock
        self.target_sock = target_sock
        self.key = key
        self.source_addr = self.source_sock.getpeername()
        self.target_addr = self.target_sock.getpeername()

    def run(self):
        while True:
            try:
                data = self.source_sock.recv(4096)
                if not data:
                    break
                logger.debug('read  %04i from %s:%d', len(data), self.source_addr[0], self.source_addr[1])
                sent = self.target_sock.send(wraptlv(TAG, encrypt(data, self.key)))
                logger.debug('write %04i to   %s:%d', sent, self.target_addr[0], self.target_addr[1])
            except socket.error as e:
                logger.error('socket error, e: %s', e)
                break
            except Exception as e:
                logger.error('unknown error, e: %s', e)
                break
        logger.debug('connection %s:%d is closed.', self.source_addr[0], self.source_addr[1])
        try:
            self.source_sock.shutdown(socket.SHUT_RDWR)
            self.target_sock.shutdown(socket.SHUT_RDWR)
        except socket.error as e:
            pass


class RecvEncrypt(threading.Thread):

    def __init__(self, source_sock, target_sock, key):
        super(RecvEncrypt, self).__init__()
        self.source_sock = source_sock
        self.target_sock = target_sock
        self.key = key
        self.source_addr = self.source_sock.getpeername()
        self.target_addr = self.target_sock.getpeername()

    def run(self):
        while True:
            try:
                data = recvtlv(self.source_sock)
                if not data:
                    break
                logger.debug('read  %04i from %s:%d', len(data) + 3, self.source_addr[0], self.source_addr[1])
                sent = self.target_sock.send(decrypt(data, self.key))
                logger.debug('write %04i to   %s:%d', sent, self.target_addr[0], self.target_addr[1])
            except socket.error as e:
                logger.error('socket error, e: %s', e)
                break
            except Exception as e:
                logger.error('unknown error, e: %s', e)
                break
        logger.debug('connection %s:%d is closed.', self.source_addr[0], self.source_addr[1])
        try:
            self.source_sock.shutdown(socket.SHUT_RDWR)
            self.target_sock.shutdown(socket.SHUT_RDWR)
        except socket.error as e:
            pass


class PyTunnel(object):

    def __init__(self, ip, port, remote_ip, remote_port, mode, key):
        self.remote_ip = remote_ip
        self.remote_port = remote_port
        self.mode = mode
        self.key = key
        self.backlog = 100
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((ip, port))
        self.sock.listen(self.backlog)

    def run(self):
        while True:
            source_sock, source_addr = self.sock.accept()
            target_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            target_sock.connect((self.remote_ip, self.remote_port))

            if self.mode == 'server':
                threads = [
                    RecvEncrypt(source_sock, target_sock, self.key),
                    SendEncrypt(target_sock, source_sock, self.key)
                ]
            elif self.mode == 'client':
                threads = [
                    SendEncrypt(source_sock, target_sock, self.key),
                    RecvEncrypt(target_sock, source_sock, self.key)
                ]

            for t in threads:
                t.setDaemon(True)
                t.start()

    def __del__(self):
        self.sock.close()


def main():
    parser = optparse.OptionParser()
    parser.add_option('-m', '--mode', dest='mode', help='client, server')
    parser.add_option('-l', '--local', dest='local_addr', help='local address:port, eg: 127.0.0.1:8080')
    parser.add_option('-r', '--remote', dest='remote_addr', help='remote address:port, eg: 192.168.0.120:8080')
    parser.add_option('-k', '--key', dest='key', help='key')
    parser.add_option('-v', '--verbose', action='store_true', dest='verbose', help='verbose')
    opts, args = parser.parse_args()

    if len(sys.argv) == 1 or len(args) > 0:
        parser.print_help()
        sys.exit()

    opts_error = False
    if opts.mode not in ('client', 'server'):
        opts_error = True
    elif len(opts.key) < 4:
        opts_error = True
    elif ':' not in opts.local_addr or ':' not in opts.remote_addr:
        opts_error = True

    if opts_error:
        parser.print_help()
        sys.exit()

    if opts.verbose:
        logging.disable(logging.NOTSET)
    else:
        logging.disable(logging.CRITICAL)

    local_ip, local_port = opts.local_addr.split(':')
    remote_ip, remote_port = opts.remote_addr.split(':')
    local_port = int(local_port)
    remote_port = int(remote_port)
    key = hashlib.sha512(opts.key).hexdigest().encode('rot-13')
    tunnel = PyTunnel(local_ip, local_port, remote_ip, remote_port, opts.mode, key)

    try:
        tunnel.run()
    except KeyboardInterrupt:
        print 'quit'
        sys.exit()


if __name__ == '__main__':
    main()
