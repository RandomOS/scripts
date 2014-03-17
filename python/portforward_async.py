#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import socket
import asyncore
import logging
import optparse


class Forwarder(asyncore.dispatcher):

    def __init__(self, ip, port, remoteip, remoteport, backlog=5):
        asyncore.dispatcher.__init__(self)
        self.remoteip = remoteip
        self.remoteport = remoteport
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((ip, port))
        self.listen(backlog)

    def handle_accept(self):
        conn, addr = self.accept()
        Sender(Receiver(conn), self.remoteip, self.remoteport)


class Receiver(asyncore.dispatcher):

    def __init__(self, conn):
        asyncore.dispatcher.__init__(self, conn)
        self.logger = logging.getLogger('Receiver')
        self.clientaddr, self.clientport = conn.getpeername()
        self.from_client_buffer = ''
        self.to_client_buffer = ''
        self.Sender = None

    def handle_connect(self):
        pass

    def handle_read(self):
        read = self.recv(4096)
        if len(read) > 0:
            self.logger.debug('read  %04i --> from %s:%d', len(read), self.clientaddr, self.clientport)
            self.from_client_buffer += read

    def writable(self):
        return (len(self.to_client_buffer) > 0)

    def handle_write(self):
        sent = self.send(self.to_client_buffer)
        self.logger.debug('write %04i <-- to   %s:%d', sent, self.clientaddr, self.clientport)
        self.to_client_buffer = self.to_client_buffer[sent:]

    def handle_close(self):
        self.close()
        if self.Sender:
            self.Sender.close()


class Sender(asyncore.dispatcher):

    def __init__(self, Receiver, remoteaddr, remoteport):
        asyncore.dispatcher.__init__(self)
        self.logger = logging.getLogger('Sender')
        self.remoteaddr = remoteaddr
        self.remoteport = remoteport
        self.Receiver = Receiver
        Receiver.Sender = self
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect((remoteaddr, remoteport))

    def handle_connect(self):
        pass

    def handle_read(self):
        read = self.recv(4096)
        if len(read) > 0:
            self.logger.debug('read  <-- %04i from %s:%d', len(read), self.remoteaddr, self.remoteport)
            self.Receiver.to_client_buffer += read

    def writable(self):
        return (len(self.Receiver.from_client_buffer) > 0)

    def handle_write(self):
        sent = self.send(self.Receiver.from_client_buffer)
        self.logger.debug('write --> %04i to   %s:%d', sent, self.remoteaddr, self.remoteport)
        self.Receiver.from_client_buffer = self.Receiver.from_client_buffer[sent:]

    def handle_close(self):
        self.close()
        self.Receiver.close()

if __name__ == '__main__':
    parser = optparse.OptionParser()

    parser.add_option(
        '-l', '--local-ip', dest='local_ip',
        help='Local IP address to bind to')
    parser.add_option(
        '-p', '--local-port',
        type='int', dest='local_port',
        help='Local port to bind to')
    parser.add_option(
        '-r', '--remote-ip', dest='remote_ip',
        help='Local IP address to bind to')
    parser.add_option(
        '-P', '--remote-port',
        type='int', dest='remote_port',
        help='Remote port to bind to')
    parser.add_option(
        '-v', '--verbose',
        action='store_true', dest='verbose',
        help='verbose')
    opts, args = parser.parse_args()

    if len(sys.argv) == 1 or len(args) > 0:
        parser.print_help()
        exit()

    if not (opts.local_ip and opts.local_port and opts.remote_ip and opts.remote_port):
        parser.print_help()
        exit()

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
        exit()
