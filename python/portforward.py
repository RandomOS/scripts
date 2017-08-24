#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import socket
import threading
import logging
import optparse

logging.basicConfig(level=logging.DEBUG, format='[%(name)s:%(lineno)03d] %(message)s')
logger = logging.getLogger('portforward')


class PipeThread(threading.Thread):

    def __init__(self, source_sock, target_sock):
        super(PipeThread, self).__init__()
        self.source_sock = source_sock
        self.target_sock = target_sock
        self.source_addr = self.source_sock.getpeername()
        self.target_addr = self.target_sock.getpeername()

    def run(self):
        while True:
            try:
                data = self.source_sock.recv(4096)
                if not data:
                    break
                logger.debug('read  %04i from %s:%d', len(data), self.source_addr[0], self.source_addr[1])
                sent = self.target_sock.send(data)
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


class Forwarder(object):

    def __init__(self, ip, port, remote_ip, remote_port):
        self.remote_ip = remote_ip
        self.remote_port = remote_port
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

            threads = [
                PipeThread(source_sock, target_sock),
                PipeThread(target_sock, source_sock)
            ]

            for t in threads:
                t.setDaemon(True)
                t.start()

    def __del__(self):
        self.sock.close()


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
        forwarder.run()
    except KeyboardInterrupt:
        print 'quit'
        sys.exit()


if __name__ == '__main__':
    main()
