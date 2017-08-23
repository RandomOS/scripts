#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import socket
import asyncore
import logging
import optparse


class Forwarder(asyncore.dispatcher):

    def __init__(self, ip, port, remote_ip, remote_port):
        asyncore.dispatcher.__init__(self)
        self.remote_ip = remote_ip
        self.remote_port = remote_port
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((ip, port))
        self.listen(100)

    def handle_accept(self):
        conn, addr = self.accept()
        Sender(Receiver(conn), self.remote_ip, self.remote_port)

    def listen(self, num):
        self.accepting = True
        return self.socket.listen(num)


class Receiver(asyncore.dispatcher):

    def __init__(self, conn):
        asyncore.dispatcher.__init__(self, conn)
        self.logger = logging.getLogger('Receiver')
        self.client_ip, self.client_port = conn.getpeername()
        self.from_client_buffer = ''
        self.to_client_buffer = ''
        self.sender = None

    def handle_connect(self):
        pass

    def handle_read(self):
        read = self.recv(4096)
        if len(read) > 0:
            self.logger.debug('read  %04i from %s:%d', len(read), self.client_ip, self.client_port)
            self.from_client_buffer += read

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


class Sender(asyncore.dispatcher):

    def __init__(self, receiver, remote_ip, remote_port):
        asyncore.dispatcher.__init__(self)
        self.logger = logging.getLogger('Sender')
        self.remote_ip = remote_ip
        self.remote_port = remote_port
        self.receiver = receiver
        receiver.sender = self
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect((remote_ip, remote_port))

    def handle_connect(self):
        pass

    def handle_read(self):
        read = self.recv(4096)
        if len(read) > 0:
            self.logger.debug('read  %04i from %s:%d', len(read), self.remote_ip, self.remote_port)
            self.receiver.to_client_buffer += read

    def writable(self):
        return len(self.receiver.from_client_buffer) > 0

    def handle_write(self):
        sent = self.send(self.receiver.from_client_buffer)
        self.logger.debug('write %04i to   %s:%d', sent, self.remote_ip, self.remote_port)
        self.receiver.from_client_buffer = self.receiver.from_client_buffer[sent:]

    def handle_close(self):
        self.close()
        self.receiver.close()


def main():
    parser = optparse.OptionParser()
    parser.add_option('-l', '--local-ip', dest='local_ip', help='local ip address to bind to')
    parser.add_option('-p', '--local-port', type='int', dest='local_port', help='local port to bind to')
    parser.add_option('-r', '--remote-ip', dest='remote_ip', help='remote ip address to bind to')
    parser.add_option('-P', '--remote-port', type='int', dest='remote_port', help='remote port to bind to')
    parser.add_option('-v', '--verbose', action='store_true', dest='verbose', help='verbose')
    opts, args = parser.parse_args()

    if len(sys.argv) == 1 or len(args) > 0:
        parser.print_help()
        sys.exit()

    if not (opts.local_ip and opts.local_port and opts.remote_ip and opts.remote_port):
        parser.print_help()
        sys.exit()

    if opts.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.CRITICAL

    logging.basicConfig(level=log_level, format='%(name)-9s: %(message)s')
    Forwarder(opts.local_ip, opts.local_port, opts.remote_ip, opts.remote_port)

    try:
        asyncore.loop(use_poll=True)
    except KeyboardInterrupt:
        print 'quit'
        sys.exit()


if __name__ == '__main__':
    main()
