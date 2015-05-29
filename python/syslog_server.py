#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
import optparse
import logging
import logging.handlers
import SocketServer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, 'logs')
LOG_FILE_PATH = os.path.join(LOG_DIR, 'syslog.log')

logger = logging.getLogger('syslog_server')


class SyslogUDPHandler(SocketServer.BaseRequestHandler):

    def setup(self):
        self.packet, self.socket = self.request
        self.ipaddress = self.client_address[0]

    def handle(self):
        data = bytes.decode(self.packet.strip('\x00'))
        data = re.sub(r'^<\d+>', '', data)
        logger.info(data)


class ThreadedUDPServer(SocketServer.ThreadingMixIn, SocketServer.UDPServer):
    pass


def main():
    parser = optparse.OptionParser()
    parser.add_option('-l', dest='ip', help='ip address to bind to')
    parser.add_option('-p', type='int', dest='port', default=514, help='port to bind to')
    opts, args = parser.parse_args()

    if not (opts.ip and opts.port):
        parser.print_help()
        sys.exit()

    if not os.path.exists(LOG_DIR):
        os.mkdir(LOG_DIR)

    handler = logging.handlers.RotatingFileHandler(filename=LOG_FILE_PATH, mode='a',
                                                   maxBytes=1024 * 1024, backupCount=5, encoding='utf-8')
    formatter = logging.Formatter(fmt='%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    try:
        address = (opts.ip, opts.port)
        server = ThreadedUDPServer(address, SyslogUDPHandler)
        server.serve_forever()
    except KeyboardInterrupt:
        print '^C received, shutting down server'


if __name__ == '__main__':
    main()
