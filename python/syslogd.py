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

lock = threading.Lock()
logger_dict = {}

syslogd_config = {
    'log_dir': None
}


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
        match = re.search(r'^<(?P<pri>\d+)>(?P<extra>.+?:) (?P<msg>.+)$', data)
        if match:
            result = match.groupdict()
            extra = result['extra']
            msg = result['msg'].lstrip('- ')
            client_ip = self.client_address[0]
            syslog_tag = extra.split(' ')[-1].strip(':')
            log_name = time.strftime('%Y/%m/%Y-%m-%d.log', time.localtime())
            log_file_path = '%s/%s/%s' % (client_ip, syslog_tag, log_name)
            log_file_path = os.path.join(syslogd_config['log_dir'], log_file_path)
            logger = self.get_logger(log_file_path)
            logger.info(msg)

    def get_logger(self, log_file_path):
        with lock:
            parent_dir = os.path.dirname(log_file_path)
            if not os.path.isdir(parent_dir):
                os.makedirs(parent_dir)
            logger_name = hashlib.md5(log_file_path).hexdigest()
            log_item = logger_dict.get(logger_name)
            if log_item:
                logger = log_item['logger']
            else:
                logger = logging.getLogger(logger_name)
                handler = logging.handlers.WatchedFileHandler(filename=log_file_path, mode='a', encoding='utf-8')
                formatter = logging.Formatter(fmt='%(message)s')
                handler.setFormatter(formatter)
                logger.addHandler(handler)
                logger.setLevel(logging.INFO)
                logger_dict[logger_name] = {
                    'logger': logger,
                    'created_at': time.time()
                }
            return logger


class ThreadedUDPServer(SocketServer.ThreadingMixIn, SocketServer.UDPServer):
    pass


def clean_logger():
    while True:
        struct_time = time.localtime()
        if struct_time.tm_hour == 0 and struct_time.tm_min == 5:
            with lock:
                log_names = []
                for log_name, log_item in logger_dict.items():
                    created_at = log_item['created_at']
                    if time.localtime(created_at).tm_mday != struct_time.tm_mday:
                        log_names.append(log_name)
                        logger = log_item['logger']
                        for handler in logger.handlers:
                            handler.close()
                for log_name in log_names:
                    del logger_dict[log_name]
            time.sleep(60)
        time.sleep(30)


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

    t = threading.Thread(target=clean_logger)
    t.setDaemon(True)
    t.start()

    try:
        address = (opts.ip, opts.port)
        server = ThreadedUDPServer(address, SyslogUDPHandler)
        server.serve_forever()
    except KeyboardInterrupt:
        print '^C received, shutting down server'


if __name__ == '__main__':
    main()
