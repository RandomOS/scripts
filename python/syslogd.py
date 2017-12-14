#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
import time
import hashlib
import optparse
import threading
import logging
import logging.handlers
import SocketServer

syslogd_config = {
    'log_dir': None
}


class SyslogUDPHandler(SocketServer.BaseRequestHandler):

    def setup(self):
        self.packet, self.socket = self.request
        self.lock = threading.Lock()
        self.logger_dict = {}

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
        match = re.search(r'^<(?P<pri>\d+)>(?P<extra>.+?:) (?P<msg>.+)$', data)
        if match:
            result = match.groupdict()
            extra = result['extra']
            msg = result['msg']
            client_ip = self.client_address[0]
            syslog_tag = extra.split(' ')[-1].strip(':')
            log_name = time.strftime('%Y/%m/%Y-%m-%d.log', time.localtime(time.time()))
            log_file_path = '%s/%s/%s' % (client_ip, syslog_tag, log_name)
            log_file_path = os.path.join(syslogd_config['log_dir'], log_file_path)
            logger = self.get_logger(log_file_path)
            logger.info(msg)

    def get_logger(self, log_file_path):
        with self.lock:
            parent_dir = os.path.dirname(log_file_path)
            if not os.path.isdir(parent_dir):
                os.makedirs(parent_dir)
            logger_name = hashlib.md5(log_file_path).hexdigest()
            logger = self.logger_dict.get(logger_name)
            if not logger:
                logger = logging.getLogger(logger_name)
                handler = logging.handlers.WatchedFileHandler(filename=log_file_path, mode='a', encoding='utf-8')
                formatter = logging.Formatter(fmt='%(message)s')
                handler.setFormatter(formatter)
                logger.addHandler(handler)
                logger.setLevel(logging.INFO)
                self.logger_dict[logger_name] = logger
            return logger


class ThreadedUDPServer(SocketServer.ThreadingMixIn, SocketServer.UDPServer):
    pass


def main():
    parser = optparse.OptionParser()
    parser.add_option('-l', dest='ip', default='127.0.0.1', help='ip address to bind to, default: 127.0.0.1')
    parser.add_option('-p', dest='port', type='int', default=5240, help='port to bind to, default: 5240')
    parser.add_option('-d', dest='log_dir', help='log directory')
    opts, args = parser.parse_args()

    if not (opts.log_dir and os.path.isdir(opts.log_dir)):
        parser.print_help()
        sys.exit()

    syslogd_config['log_dir'] = opts.log_dir

    try:
        address = (opts.ip, opts.port)
        server = ThreadedUDPServer(address, SyslogUDPHandler)
        server.serve_forever()
    except KeyboardInterrupt:
        print '^C received, shutting down server'


if __name__ == '__main__':
    main()
