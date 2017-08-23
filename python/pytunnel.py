#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import socket
import struct
import asyncore
import logging
import optparse
from itertools import cycle, izip

TAG = 128


def encrypt(value, key):
    encrypt_value = ''.join(chr(ord(c) ^ ord(k)) for c, k in izip(value, cycle(key)))
    return encrypt_value


def decrypt(value, key):
    return encrypt(value, key)


def wraptlv(tag, value):
    tag = struct.pack('B', tag)
    length = len(value)
    length = struct.pack('!H', length)
    data = tag + length + value
    return data


class PyTunnel(asyncore.dispatcher):

    def __init__(self, ip, port, remote_ip, remote_port, mode, key):
        asyncore.dispatcher.__init__(self)
        self.remote_ip = remote_ip
        self.remote_port = remote_port
        self.mode = mode
        self.key = key
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((ip, port))
        self.listen(100)

    def handle_accept(self):
        conn, addr = self.accept()
        Sender(Receiver(conn, self.mode, self.key), self.remote_ip, self.remote_port, self.mode, self.key)

    def listen(self, num):
        self.accepting = True
        return self.socket.listen(num)


class Receiver(asyncore.dispatcher):

    def __init__(self, conn, mode, key):
        asyncore.dispatcher.__init__(self, conn)
        self.logger = logging.getLogger('Receiver')
        self.client_ip, self.client_port = conn.getpeername()
        self.from_client_buffer = ''
        self.to_client_buffer = ''
        self.sender = None
        self.mode = mode
        self.key = key

    def handle_connect(self):
        pass

    def handle_read(self):
        if self.mode == 'server':
            read = self.recvpacket()
            if len(read) > 0:
                self.logger.debug('read  %04i from %s:%d', len(read), self.client_ip, self.client_port)
                self.from_client_buffer += decrypt(read, self.key)
        elif self.mode == 'client':
            read = self.recv(4096)
            if len(read) > 0:
                self.logger.debug('read  %04i from %s:%d', len(read), self.client_ip, self.client_port)
                self.from_client_buffer += wraptlv(TAG, encrypt(read, self.key))

    def writable(self):
        return len(self.to_client_buffer) > 0

    def handle_write(self):
        sent = self.send(self.to_client_buffer)
        self.logger.debug('write %04i to   %s:%d', sent, self.client_ip, self.client_port)
        self.to_client_buffer = self.to_client_buffer[sent:]

    def handle_close(self):
        self.close()
        if self.sender:
            self.sender.close()

    def recvpacket(self):
        data = self.recv(1)
        if not data:
            return data
        tag = struct.unpack('B', data)[0]
        if tag != TAG:
            self.handle_close()
            return ''
        data = self.recv(2)
        if not data:
            return data
        length = struct.unpack('!H', data)[0]
        data = self.recv(length)
        return data


class Sender(asyncore.dispatcher):

    def __init__(self, receiver, remote_ip, remote_port, mode, key):
        asyncore.dispatcher.__init__(self)
        self.logger = logging.getLogger('Sender')
        self.remote_ip = remote_ip
        self.remote_port = remote_port
        self.mode = mode
        self.key = key
        self.receiver = receiver
        receiver.sender = self
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect((remote_ip, remote_port))

    def handle_connect(self):
        pass

    def handle_read(self):
        if self.mode == 'server':
            read = self.recv(4096)
            if len(read) > 0:
                self.logger.debug('read  %04i from %s:%d', len(read), self.remote_ip, self.remote_port)
                self.receiver.to_client_buffer += wraptlv(TAG, encrypt(read, self.key))
        elif self.mode == 'client':
            read = self.recvpacket()
            if len(read) > 0:
                self.logger.debug('read  %04i from %s:%d', len(read), self.remote_ip, self.remote_port)
                self.receiver.to_client_buffer += decrypt(read, self.key)

    def writable(self):
        return len(self.receiver.from_client_buffer) > 0

    def handle_write(self):
        sent = self.send(self.receiver.from_client_buffer)
        self.logger.debug('write %04i to   %s:%d', sent, self.remote_ip, self.remote_port)
        self.receiver.from_client_buffer = self.receiver.from_client_buffer[sent:]

    def handle_close(self):
        self.close()
        self.receiver.close()

    def recvpacket(self):
        data = self.recv(1)
        if not data:
            return data
        tag = struct.unpack('B', data)[0]
        if tag != TAG:
            self.handle_close()
            return ''
        data = self.recv(2)
        if not data:
            return data
        length = struct.unpack('!H', data)[0]
        data = self.recv(length)
        return data


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
    elif len(opts.key) < 5:
        opts_error = True
    elif ':' not in opts.local_addr or ':' not in opts.remote_addr:
        opts_error = True

    if opts_error:
        parser.print_help()
        sys.exit()

    if opts.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.CRITICAL

    local_ip, local_port = opts.local_addr.split(':')
    remote_ip, remote_port = opts.remote_addr.split(':')
    local_port = int(local_port)
    remote_port = int(remote_port)
    logging.basicConfig(level=log_level, format='%(name)-9s: %(message)s')
    PyTunnel(local_ip, local_port, remote_ip, remote_port, opts.mode, opts.key)

    try:
        asyncore.loop(use_poll=True)
    except KeyboardInterrupt:
        print 'quit'
        sys.exit()


if __name__ == '__main__':
    main()
