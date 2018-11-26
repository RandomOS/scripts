#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import socket
import asyncore
import logging
import optparse

logging.basicConfig(level=logging.DEBUG, format='[%(name)s:%(lineno)03d] %(message)s')
logger = logging.getLogger('portforward')


class Forwarder(asyncore.dispatcher):

    def __init__(self, ip, port, remote_ip, remote_port):
        asyncore.dispatcher.__init__(self)
        self.remote_ip = remote_ip
        self.remote_port = remote_port
        self.backlog = 100
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((ip, port))
        self.listen(self.backlog)

    def handle_accept(self):
        conn, addr = self.accept()
        Sender(Receiver(conn), self.remote_ip, self.remote_port)

    def listen(self, num):
        self.accepting = True
        return self.socket.listen(num)


class Receiver(asyncore.dispatcher):

    def __init__(self, conn):
        asyncore.dispatcher.__init__(self, conn)
        self.client_ip, self.client_port = conn.getpeername()
        self.from_client_buffer = ''
        self.to_client_buffer = ''
        self.sender = None

    def readable(self):
        return len(self.from_client_buffer) < 40960

    def writable(self):
        return len(self.to_client_buffer) > 0

    def handle_connect(self):
        pass

    def handle_read(self):
        read = self.recv(4096)
        if read:
            logger.debug('read  %04i from %s:%d', len(read), self.client_ip, self.client_port)
            self.from_client_buffer += read

    def handle_write(self):
        sent = self.send(self.to_client_buffer)
        logger.debug('write %04i to   %s:%d', sent, self.client_ip, self.client_port)
        self.to_client_buffer = self.to_client_buffer[sent:]

    def handle_close(self):
        self.close()
        if self.sender:
            self.sender.close()


class Sender(asyncore.dispatcher):

    def __init__(self, receiver, remote_ip, remote_port):
        asyncore.dispatcher.__init__(self)
        self.remote_ip = remote_ip
        self.remote_port = remote_port
        self.receiver = receiver
        receiver.sender = self
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
        read = self.recv(4096)
        if read:
            logger.debug('read  %04i from %s:%d', len(read), self.remote_ip, self.remote_port)
            self.receiver.to_client_buffer += read

    def handle_write(self):
        sent = self.send(self.receiver.from_client_buffer)
        logger.debug('write %04i to   %s:%d', sent, self.remote_ip, self.remote_port)
        self.receiver.from_client_buffer = self.receiver.from_client_buffer[sent:]

    def handle_close(self):
        self.close()
        self.receiver.close()


def main():
    parser = optparse.OptionParser()
    parser.add_option('-l', '--local', dest='local_addr', help='local address:port, eg: 127.0.0.1:8080')
    parser.add_option('-r', '--remote', dest='remote_addr', help='remote address:port, eg: 192.168.0.120:8080')
    parser.add_option('-v', '--verbose', action='store_true', dest='verbose', help='verbose')
    opts, args = parser.parse_args()

    if len(sys.argv) == 1 or len(args) > 0:
        parser.print_help()
        sys.exit()

    if ':' not in opts.local_addr or ':' not in opts.remote_addr:
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
    forwarder = Forwarder(local_ip, local_port, remote_ip, remote_port)

    try:
        asyncore.loop(use_poll=True)
    except KeyboardInterrupt:
        print 'quit'
        sys.exit()


if __name__ == '__main__':
    main()
