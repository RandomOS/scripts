#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import string
import socket
import struct
import random
import hashlib
import logging
import optparse
import threading

logging.basicConfig(level=logging.DEBUG, format='[%(name)s:%(lineno)03d] %(message)s')
logger = logging.getLogger('pytunnel')

TAG = 128

trans_table = {
    'encode_table': None,
    'decode_table': None
}


def get_trans_table(key):
    if trans_table['encode_table'] and trans_table['decode_table']:
        return trans_table['encode_table'], trans_table['decode_table']
    original_data = string.maketrans('', '')
    encoded_data = string.maketrans('', '')
    encoded_data = bytearray(encoded_data)
    random.seed(int(key, 16))
    random.shuffle(encoded_data)
    encoded_data = str(encoded_data)
    trans_table['encode_table'] = string.maketrans(original_data, encoded_data)
    trans_table['decode_table'] = string.maketrans(encoded_data, original_data)
    return trans_table['encode_table'], trans_table['decode_table']


def encrypt(value, key):
    encode_table, _ = get_trans_table(key)
    result = string.translate(value, encode_table)
    return result


def decrypt(value, key):
    _, decode_table = get_trans_table(key)
    result = string.translate(value, decode_table)
    return result


def wraptlv(tag, value):
    tag = struct.pack('B', tag)
    length = len(value)
    length = struct.pack('!H', length)
    data = tag + length + value
    return data


def recvall(sock, size):
    """Read exactly size bytes. Return None on EOF, '' when size is 0."""
    data = ''
    while len(data) < size:
        buf = sock.recv(size - len(data))
        if not buf:
            return None
        data += buf
    return data


def recvtlv(sock):
    """Read one frame. Return None on EOF or desync, '' for an empty frame."""
    data = recvall(sock, 1)
    if data is None:
        return None
    tag = struct.unpack('B', data)[0]
    if tag != TAG:
        # the stream is out of sync, there is no way to resynchronise
        logger.error('bad tag %d, expected %d', tag, TAG)
        return None
    data = recvall(sock, 2)
    if data is None:
        return None
    length = struct.unpack('!H', data)[0]
    return recvall(sock, length)


class Link(object):
    """Shared teardown state for the two relay threads of one connection."""

    def __init__(self, sock_a, sock_b):
        self.socks = (sock_a, sock_b)
        self.lock = threading.Lock()
        self.done = 0

    def finish(self, abort):
        if abort:
            # the connection is broken, kick the peer thread out of its read
            for sock in self.socks:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except socket.error:
                    pass
        with self.lock:
            self.done += 1
            last = self.done == len(self.socks)
        if last:
            for sock in self.socks:
                try:
                    sock.close()
                except socket.error:
                    pass


class SendEncrypt(threading.Thread):

    def __init__(self, source_sock, target_sock, key, link, source_addr, target_addr):
        super(SendEncrypt, self).__init__()
        self.source_sock = source_sock
        self.target_sock = target_sock
        self.key = key
        self.link = link
        self.source_addr = source_addr
        self.target_addr = target_addr

    def run(self):
        abort = False
        while True:
            try:
                data = self.source_sock.recv(4096)
                if not data:
                    break
                logger.debug('read  %04i from %s:%d', len(data), self.source_addr[0], self.source_addr[1])
                frame = wraptlv(TAG, encrypt(data, self.key))
                self.target_sock.sendall(frame)
                logger.debug('write %04i to   %s:%d', len(frame), self.target_addr[0], self.target_addr[1])
            except socket.error as e:
                logger.error('socket error, e: %s', e)
                abort = True
                break
            except Exception as e:
                logger.error('unknown error, e: %s', e)
                abort = True
                break
        logger.debug('connection %s:%d is closed.', self.source_addr[0], self.source_addr[1])
        if not abort:
            # propagate the half close so the peer can still send its reply
            try:
                self.target_sock.shutdown(socket.SHUT_WR)
            except socket.error:
                pass
        self.link.finish(abort)


class RecvEncrypt(threading.Thread):

    def __init__(self, source_sock, target_sock, key, link, source_addr, target_addr):
        super(RecvEncrypt, self).__init__()
        self.source_sock = source_sock
        self.target_sock = target_sock
        self.key = key
        self.link = link
        self.source_addr = source_addr
        self.target_addr = target_addr

    def run(self):
        abort = False
        while True:
            try:
                data = recvtlv(self.source_sock)
                if data is None:
                    break
                logger.debug('read  %04i from %s:%d', len(data) + 3, self.source_addr[0], self.source_addr[1])
                if not data:
                    continue
                self.target_sock.sendall(decrypt(data, self.key))
                logger.debug('write %04i to   %s:%d', len(data), self.target_addr[0], self.target_addr[1])
            except socket.error as e:
                logger.error('socket error, e: %s', e)
                abort = True
                break
            except Exception as e:
                logger.error('unknown error, e: %s', e)
                abort = True
                break
        logger.debug('connection %s:%d is closed.', self.source_addr[0], self.source_addr[1])
        if not abort:
            # propagate the half close so the peer can still send its reply
            try:
                self.target_sock.shutdown(socket.SHUT_WR)
            except socket.error:
                pass
        self.link.finish(abort)


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
            try:
                source_sock, source_addr = self.sock.accept()
            except socket.error as e:
                logger.error('accept error, e: %s', e)
                continue
            try:
                self.handle(source_sock, source_addr)
            except Exception as e:
                # never let a single bad connection kill the accept loop
                logger.error('connection setup error, e: %s', e)
                try:
                    source_sock.close()
                except socket.error:
                    pass

    def handle(self, source_sock, source_addr):
        target_addr = (self.remote_ip, self.remote_port)
        target_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            target_sock.connect(target_addr)
        except socket.error as e:
            source_sock.close()
            target_sock.close()
            return

        link = Link(source_sock, target_sock)
        if self.mode == 'server':
            threads = [
                RecvEncrypt(source_sock, target_sock, self.key, link, source_addr, target_addr),
                SendEncrypt(target_sock, source_sock, self.key, link, target_addr, source_addr)
            ]
        elif self.mode == 'client':
            threads = [
                SendEncrypt(source_sock, target_sock, self.key, link, source_addr, target_addr),
                RecvEncrypt(target_sock, source_sock, self.key, link, target_addr, source_addr)
            ]
        else:
            source_sock.close()
            target_sock.close()
            raise ValueError('unknown mode: %s' % self.mode)

        for t in threads:
            t.setDaemon(True)
            t.start()

    def __del__(self):
        self.sock.close()


def parse_addr(addr):
    """Parse an 'address:port' pair. Return None when it is missing or malformed."""
    if not addr or addr.count(':') != 1:
        return None
    ip, port = addr.split(':')
    if not ip or not port.isdigit():
        return None
    port = int(port)
    if not 0 < port < 65536:
        return None
    return ip, port


def main():
    parser = optparse.OptionParser(version='0.1.0')
    parser.add_option('-m', '--mode', dest='mode', help='client, server')
    parser.add_option('-l', '--local', dest='local_addr', help='local address:port, eg: 127.0.0.1:8080')
    parser.add_option('-r', '--remote', dest='remote_addr', help='remote address:port, eg: 192.168.0.120:8080')
    parser.add_option('-k', '--key', dest='key', help='key, eg: helloworld')
    parser.add_option('-v', '--verbose', action='store_true', dest='verbose', help='verbose')
    opts, args = parser.parse_args()

    if len(sys.argv) == 1 or len(args) > 0:
        parser.print_help()
        sys.exit()

    local = parse_addr(opts.local_addr)
    remote = parse_addr(opts.remote_addr)

    opts_error = False
    if opts.mode not in ('client', 'server'):
        opts_error = True
    if not opts.key:
        opts_error = True
    if local is None or remote is None:
        opts_error = True

    if opts_error:
        parser.print_help()
        sys.exit()

    if opts.verbose:
        logging.disable(logging.NOTSET)
    else:
        logging.disable(logging.CRITICAL)

    local_ip, local_port = local
    remote_ip, remote_port = remote
    key = hashlib.sha1(opts.key).hexdigest()
    tunnel = PyTunnel(local_ip, local_port, remote_ip, remote_port, opts.mode, key)

    try:
        tunnel.run()
    except KeyboardInterrupt:
        print 'quit'
        sys.exit()


if __name__ == '__main__':
    main()
