#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import string
import socket
import struct
import random
import hashlib
import asyncore
import logging
import optparse

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


class PyTunnel(asyncore.dispatcher):

    def __init__(self, ip, port, remote_ip, remote_port, mode, key):
        asyncore.dispatcher.__init__(self)
        self.remote_ip = remote_ip
        self.remote_port = remote_port
        self.mode = mode
        self.key = key
        self.backlog = 100
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.set_reuse_port()
        self.bind((ip, port))
        self.listen(self.backlog)

    def handle_accept(self):
        conn, addr = self.accept()
        Sender(Receiver(conn, self.mode, self.key), self.remote_ip, self.remote_port, self.mode, self.key)

    def listen(self, num):
        self.accepting = True
        return self.socket.listen(num)

    def set_reuse_port(self):
        try:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except (AttributeError, socket.error):
            pass


class Receiver(asyncore.dispatcher):

    def __init__(self, conn, mode, key):
        asyncore.dispatcher.__init__(self, conn)
        self.client_ip, self.client_port = conn.getpeername()
        self.mode = mode
        self.key = key
        self.from_client_buffer = ''
        self.to_client_buffer = ''
        self.at_tlv_start_pos = True
        self.tag_and_length = ''
        self.value = ''
        self.length = 0
        self.sender = None

    def readable(self):
        return len(self.from_client_buffer) < 40960

    def writable(self):
        return len(self.to_client_buffer) > 0

    def handle_connect(self):
        pass

    def handle_read(self):
        if self.mode == 'server':
            if self.at_tlv_start_pos:
                tag, length = self.read_tag_and_length()
                if tag is not None and length is not None:
                    if tag != TAG or length == 0:
                        self.handle_close()
                        return
                    self.at_tlv_start_pos = False
                    self.tag_and_length = ''
                    self.length = length
            else:
                value = self.read_value()
                if value:
                    self.from_client_buffer += decrypt(value, self.key)
                    self.at_tlv_start_pos = True
                    self.value = ''
                    self.length = 0
        elif self.mode == 'client':
            read = self.recv(4096)
            if read:
                logger.debug('read  %04i from %s:%d', len(read), self.client_ip, self.client_port)
                self.from_client_buffer += wraptlv(TAG, encrypt(read, self.key))

    def handle_write(self):
        sent = self.send(self.to_client_buffer)
        logger.debug('write %04i to   %s:%d', sent, self.client_ip, self.client_port)
        self.to_client_buffer = self.to_client_buffer[sent:]

    def handle_close(self):
        self.close()
        if self.sender:
            self.sender.close()

    def read_tag_and_length(self):
        tag_and_length_size = 3
        remain_size = tag_and_length_size - len(self.tag_and_length)
        if remain_size > 0:
            read = self.recv(remain_size)
            if read:
                logger.debug('read  %04i from %s:%d', len(read), self.client_ip, self.client_port)
                self.tag_and_length += read
                remain_size = tag_and_length_size - len(self.tag_and_length)
        if remain_size == 0:
            tag = struct.unpack('B', self.tag_and_length[0])[0]
            length = struct.unpack('!H', self.tag_and_length[1:3])[0]
            return tag, length
        return None, None

    def read_value(self):
        remain_size = self.length - len(self.value)
        if remain_size > 0:
            read = self.recv(remain_size)
            if read:
                logger.debug('read  %04i from %s:%d', len(read), self.client_ip, self.client_port)
                self.value += read
                remain_size = self.length - len(self.value)
        if remain_size == 0:
            return self.value


class Sender(asyncore.dispatcher):

    def __init__(self, receiver, remote_ip, remote_port, mode, key):
        asyncore.dispatcher.__init__(self)
        self.remote_ip = remote_ip
        self.remote_port = remote_port
        self.mode = mode
        self.key = key
        self.at_tlv_start_pos = True
        self.tag_and_length = ''
        self.value = ''
        self.length = 0
        self.receiver = receiver
        self.receiver.sender = self
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect((remote_ip, remote_port))

    def connect(self, address):
        try:
            asyncore.dispatcher.connect(self, address)
        except socket.error as e:
            self.handle_close()

    def readable(self):
        return len(self.receiver.to_client_buffer) < 40960

    def writable(self):
        return len(self.receiver.from_client_buffer) > 0

    def handle_connect(self):
        pass

    def handle_read(self):
        if self.mode == 'server':
            read = self.recv(4096)
            if read:
                logger.debug('read  %04i from %s:%d', len(read), self.remote_ip, self.remote_port)
                self.receiver.to_client_buffer += wraptlv(TAG, encrypt(read, self.key))
        elif self.mode == 'client':
            if self.at_tlv_start_pos:
                tag, length = self.read_tag_and_length()
                if tag is not None and length is not None:
                    if tag != TAG or length == 0:
                        self.handle_close()
                        return
                    self.at_tlv_start_pos = False
                    self.tag_and_length = ''
                    self.length = length
            else:
                value = self.read_value()
                if value:
                    self.receiver.to_client_buffer += decrypt(value, self.key)
                    self.at_tlv_start_pos = True
                    self.value = ''
                    self.length = 0

    def handle_write(self):
        sent = self.send(self.receiver.from_client_buffer)
        logger.debug('write %04i to   %s:%d', sent, self.remote_ip, self.remote_port)
        self.receiver.from_client_buffer = self.receiver.from_client_buffer[sent:]

    def handle_close(self):
        self.close()
        self.receiver.close()

    def read_tag_and_length(self):
        tag_and_length_size = 3
        remain_size = tag_and_length_size - len(self.tag_and_length)
        if remain_size > 0:
            read = self.recv(remain_size)
            if read:
                logger.debug('read  %04i from %s:%d', len(read), self.remote_ip, self.remote_port)
                self.tag_and_length += read
                remain_size = tag_and_length_size - len(self.tag_and_length)
        if remain_size == 0:
            tag = struct.unpack('B', self.tag_and_length[0])[0]
            length = struct.unpack('!H', self.tag_and_length[1:3])[0]
            return tag, length
        return None, None

    def read_value(self):
        remain_size = self.length - len(self.value)
        if remain_size > 0:
            read = self.recv(remain_size)
            if read:
                logger.debug('read  %04i from %s:%d', len(read), self.remote_ip, self.remote_port)
                self.value += read
                remain_size = self.length - len(self.value)
        if remain_size == 0:
            return self.value


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

    opts_error = False
    if opts.mode not in ('client', 'server'):
        opts_error = True
    elif not (opts.key and len(opts.key) > 4):
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
    key = hashlib.sha1(opts.key).hexdigest()
    tunnel = PyTunnel(local_ip, local_port, remote_ip, remote_port, opts.mode, key)

    try:
        asyncore.loop(use_poll=True)
    except KeyboardInterrupt:
        print 'quit'
        sys.exit()


if __name__ == '__main__':
    main()
