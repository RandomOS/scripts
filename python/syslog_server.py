#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

    def handle(self):
        data = None
        encodings = ['utf-8', 'gbk']
        for encoding in encodings:
            try:
                data = bytes.decode(self.packet.strip('\x00'), encoding)
            except UnicodeDecodeError:
                continue
            else:
                break
        if data is None:
            data = bytes.decode(self.packet.strip('\x00'), 'utf-8', 'ignore')
        if data.strip() == 'ping':
            self.socket.sendto('pong', self.client_address)
            return
        match = re.search(r'^<\d+>', data)
        if match:
            data = data[len(match.group(0)):]
            logger.info(data)


def main():
    parser = optparse.OptionParser()
    parser.add_option('-l', dest='ip', default='127.0.0.1', help='ip address to bind to, default: 127.0.0.1')
    parser.add_option('-p', dest='port', type='int', default=5140, help='port to bind to, default: 5140')
    parser.add_option('-f', dest='log_file_path', help='log file path')
    parser.add_option('-m', dest='max_size', type='int', default=100, help='log file max size (MB), default: 100')
    parser.add_option('-c', dest='backup_count', type='int', default=5, help='log file backup count, default: 5')
    opts, args = parser.parse_args()

    if not opts.log_file_path:
        parser.print_help()
        sys.exit()

    log_file_path = opts.log_file_path
    max_bytes = opts.max_size * 1024 * 1024
    backup_count = opts.backup_count

    handler = logging.handlers.RotatingFileHandler(
        filename=log_file_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        mode='a',
        encoding='utf-8'
    )
    formatter = logging.Formatter(fmt='%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    try:
        address = (opts.ip, opts.port)
        server = SocketServer.UDPServer(address, SyslogUDPHandler)
        server.serve_forever()
    except KeyboardInterrupt:
        print '^C received, shutting down server'


if __name__ == '__main__':
    main()
