#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import time
import signal
import optparse
import logging
import logging.handlers

logger = logging.getLogger('send_syslog')


def exit_handler(signal, frame):
    sys.exit()


def main():
    parser = optparse.OptionParser()
    parser.add_option('--host', dest='host', default='127.0.0.1', help='syslog server ip, default: 127.0.0.1')
    parser.add_option('--port', dest='port', type='int', default=5140, help='syslog server port, default: 5140')
    parser.add_option('--tag', dest='syslog_tag', help='syslog tag')
    opts, args = parser.parse_args()

    if not opts.syslog_tag:
        parser.print_help()
        sys.exit()

    signal.signal(signal.SIGINT, exit_handler)
    syslog_tag = opts.syslog_tag.replace(':', '')
    syslog_format = '%s: %%(message)s' % syslog_tag
    handler = logging.handlers.SysLogHandler(address=(opts.host, opts.port))
    formatter = logging.Formatter(fmt=syslog_format)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    while True:
        line = sys.stdin.readline()
        if not line:
            time.sleep(0.1)
        logger.info(line.strip())


if __name__ == '__main__':
    main()
