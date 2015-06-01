#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
import optparse
import logging
import logging.handlers
import SocketServer

logger = logging.getLogger('syslog_server')


class SyslogUDPHandler(SocketServer.BaseRequestHandler):

    def setup(self):
        self.packet, self.socket = self.request
        self.ipaddress = self.client_address[0]

    def handle(self):
        data = bytes.decode(self.packet.strip('\x00'))
        m = re.search(r'^<\d+>', data)
        if m:
            data = data.replace(m.group(0), '')
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

    base_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.join(base_dir, 'logs')
    log_file_path = os.path.join(log_dir, 'syslog.log')

    if not os.path.exists(log_dir):
        os.mkdir(log_dir)

    handler = logging.handlers.RotatingFileHandler(filename=log_file_path, mode='a',
                                                   maxBytes=10 * 1024 * 1024, backupCount=5, encoding='utf-8')
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
