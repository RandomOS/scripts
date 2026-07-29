#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import string
import socket
import struct
import random
import hashlib
import asyncore
import logging
import optparse

logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s] [%(name)s:%(lineno)03d] %(message)s')
logger = logging.getLogger('pytunnel')

TAG = 128

trans_table = {
    'encode_table': None,
    'decode_table': None
}


def get_trans_table(key):
    if trans_table['encode_table'] and trans_table['decode_table']:
        return trans_table['encode_table'], trans_table['decode_table']
    original_data = string.maketrans('', '')
    encoded_data = string.maketrans('', '')
    encoded_data = bytearray(encoded_data)
    random.seed(int(key, 16))
    random.shuffle(encoded_data)
    encoded_data = str(encoded_data)
    trans_table['encode_table'] = string.maketrans(original_data, encoded_data)
    trans_table['decode_table'] = string.maketrans(encoded_data, original_data)
    return trans_table['encode_table'], trans_table['decode_table']


def encrypt(value, key):
    encode_table, _ = get_trans_table(key)
    result = string.translate(value, encode_table)
    return result


def decrypt(value, key):
    _, decode_table = get_trans_table(key)
    result = string.translate(value, decode_table)
    return result


def wraptlv(tag, value):
    tag = struct.pack('B', tag)
    length = len(value)
    length = struct.pack('!H', length)
    data = tag + length + value
    return data


class Relay(asyncore.dispatcher):
    """Half of a tunnelled connection, closing in step with its peer.

    A peer that reached EOF must not tear the pair down straight away: the
    other direction may still hold data the client is waiting for. Instead the
    write side is shut down once the shared buffer has been flushed, and the
    sockets go away only after both directions are done.

    Subclasses provide peer() and output_buffer(), and carry the TLV decoder
    state (at_tlv_start_pos, tag_and_length, value, length) this class reads.
    """

    def __init__(self, sock=None):
        asyncore.dispatcher.__init__(self, sock)
        self.read_eof = False
        self.write_closed = False

    def peer(self):
        raise NotImplementedError

    def output_buffer(self):
        """Bytes still waiting to be written to this side."""
        raise NotImplementedError

    def decoder_idle(self):
        """False while a frame has been started but not fully decoded yet."""
        return self.at_tlv_start_pos and not self.tag_and_length

    def frame_decoded(self):
        """A frame just landed in the peer buffer, it may unblock its close."""
        peer = self.peer()
        if peer is not None and peer.connected:
            peer.flush_write()

    def decoder_state(self):
        peer = self.peer()
        produced = len(peer.output_buffer()) if peer is not None else 0
        return (produced, self.at_tlv_start_pos,
                self.tag_and_length, self.value, self.length)

    def decode_progress(self):
        """Run one read step, tell whether it moved the decoder forward."""
        before = self.decoder_state()
        self.handle_read()
        return before != self.decoder_state()

    def writable(self):
        return len(self.output_buffer()) > 0

    def handle_close(self):
        if self.read_eof:
            # already half closed, the socket just keeps reporting EOF
            return
        # this side is done reading, tell the other one to stop writing to us
        # (set first: recv() calls handle_close() again once it hits EOF)
        self.read_eof = True
        # EOF says no more bytes will arrive, but the kernel buffer may still
        # hold whole frames, decode them before letting the peer shut down
        while self.decode_progress():
            pass
        peer = self.peer()
        if peer is None or peer.socket is None:
            self.close_pair()
            return
        peer.close_write()

    def close_write(self):
        """Stop writing to this side once the pending output has been flushed.

        The peer reached EOF, but bytes it already read may still be sitting in
        its decoder, so the write side stays open until the peer is really done.
        """
        self.write_closed = True
        self.flush_write()

    def flush_write(self):
        if not self.write_closed or self.output_buffer():
            return
        peer = self.peer()
        if peer is not None and peer.connected and not peer.decoder_idle():
            # a partially decoded frame is still on its way to us
            return
        try:
            self.socket.shutdown(socket.SHUT_WR)
        except socket.error:
            pass
        self.close_when_idle()

    def idle(self):
        """True once this side can neither receive nor deliver anything."""
        return self.write_closed and not self.output_buffer()

    def close_when_idle(self):
        """Drop the pair once neither direction can carry anything anymore."""
        peer = self.peer()
        if peer is None or peer.socket is None:
            if not self.output_buffer():
                self.close_pair()
        elif self.idle() and peer.idle():
            self.close_pair()

    def close_pair(self):
        peer = self.peer()
        self.close()
        if peer is not None:
            peer.close()


class PyTunnel(asyncore.dispatcher):

    def __init__(self, ip, port, remote_ip, remote_port, mode, key):
        asyncore.dispatcher.__init__(self)
        self.remote_ip = remote_ip
        self.remote_port = remote_port
        self.mode = mode
        self.key = key
        self.backlog = 100
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.set_reuse_port()
        self.bind((ip, port))
        self.listen(self.backlog)

    def handle_accept(self):
        pair = self.accept()
        if pair is None:
            # EWOULDBLOCK, ECONNABORTED or EAGAIN, there is nothing to accept
            return
        conn, addr = pair
        receiver = Receiver(conn, self.mode, self.key)
        if not receiver.connected:
            # the peer is already gone, do not open a connection to the remote
            return
        Sender(receiver, self.remote_ip, self.remote_port, self.mode, self.key)

    def handle_error(self):
        # the default handler closes the channel, which would kill the listener
        logger.exception('unexpected error while accepting a connection')

    def listen(self, num):
        self.accepting = True
        return self.socket.listen(num)

    def set_reuse_port(self):
        try:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except (AttributeError, socket.error):
            pass


class Receiver(Relay):

    def __init__(self, conn, mode, key):
        Relay.__init__(self, conn)
        self.mode = mode
        self.key = key
        self.from_client_buffer = ''
        self.to_client_buffer = ''
        self.at_tlv_start_pos = True
        self.tag_and_length = ''
        self.value = ''
        self.length = 0
        self.sender = None
        self.client_ip = '?'
        self.client_port = 0
        try:
            self.client_ip, self.client_port = conn.getpeername()
        except socket.error as e:
            self.handle_close()
            return

    def peer(self):
        return self.sender

    def output_buffer(self):
        return self.to_client_buffer

    def readable(self):
        return not self.read_eof and len(self.from_client_buffer) < 40960

    def handle_connect(self):
        pass

    def handle_read(self):
        if self.mode == 'server':
            if self.at_tlv_start_pos:
                tag, length = self.read_tag_and_length()
                if tag is not None and length is not None:
                    if tag != TAG:
                        # the stream is out of sync, there is no way to resynchronise
                        logger.error('bad tag %d from %s:%d', tag, self.client_ip, self.client_port)
                        self.handle_close()
                        return
                    self.tag_and_length = ''
                    if length == 0:
                        # an empty frame carries no payload, wait for the next one
                        return
                    self.at_tlv_start_pos = False
                    self.length = length
            else:
                value = self.read_value()
                if value:
                    self.from_client_buffer += decrypt(value, self.key)
                    self.at_tlv_start_pos = True
                    self.value = ''
                    self.length = 0
                    self.frame_decoded()
        elif self.mode == 'client':
            read = self.recv(4096)
            if read:
                logger.debug('read  %04i from %s:%d', len(read), self.client_ip, self.client_port)
                self.from_client_buffer += wraptlv(TAG, encrypt(read, self.key))

    def handle_write(self):
        sent = self.send(self.to_client_buffer)
        logger.debug('write %04i to   %s:%d', sent, self.client_ip, self.client_port)
        self.to_client_buffer = self.to_client_buffer[sent:]
        self.flush_write()

    def handle_error(self):
        logger.exception('error on connection from %s:%d', self.client_ip, self.client_port)
        self.close_pair()

    def read_tag_and_length(self):
        tag_and_length_size = 3
        remain_size = tag_and_length_size - len(self.tag_and_length)
        if remain_size > 0:
            read = self.recv(remain_size)
            if read:
                logger.debug('read  %04i from %s:%d', len(read), self.client_ip, self.client_port)
                self.tag_and_length += read
                remain_size = tag_and_length_size - len(self.tag_and_length)
        if remain_size == 0:
            tag = struct.unpack('B', self.tag_and_length[0])[0]
            length = struct.unpack('!H', self.tag_and_length[1:3])[0]
            return tag, length
        return None, None

    def read_value(self):
        remain_size = self.length - len(self.value)
        if remain_size > 0:
            read = self.recv(remain_size)
            if read:
                logger.debug('read  %04i from %s:%d', len(read), self.client_ip, self.client_port)
                self.value += read
                remain_size = self.length - len(self.value)
        if remain_size == 0:
            return self.value


class Sender(Relay):

    def __init__(self, receiver, remote_ip, remote_port, mode, key):
        Relay.__init__(self)
        self.remote_ip = remote_ip
        self.remote_port = remote_port
        self.mode = mode
        self.key = key
        self.at_tlv_start_pos = True
        self.tag_and_length = ''
        self.value = ''
        self.length = 0
        self.receiver = receiver
        self.receiver.sender = self
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect((remote_ip, remote_port))

    def connect(self, address):
        try:
            asyncore.dispatcher.connect(self, address)
        except socket.error as e:
            logger.error('cannot connect to %s:%d, e: %s', address[0], address[1], e)
            self.close_pair()

    def peer(self):
        return self.receiver

    def output_buffer(self):
        return self.receiver.from_client_buffer

    def readable(self):
        return not self.read_eof and len(self.receiver.to_client_buffer) < 40960

    def handle_connect(self):
        pass

    def handle_read(self):
        if self.mode == 'server':
            read = self.recv(4096)
            if read:
                logger.debug('read  %04i from %s:%d', len(read), self.remote_ip, self.remote_port)
                self.receiver.to_client_buffer += wraptlv(TAG, encrypt(read, self.key))
        elif self.mode == 'client':
            if self.at_tlv_start_pos:
                tag, length = self.read_tag_and_length()
                if tag is not None and length is not None:
                    if tag != TAG:
                        # the stream is out of sync, there is no way to resynchronise
                        logger.error('bad tag %d from %s:%d', tag, self.remote_ip, self.remote_port)
                        self.close_pair()
                        return
                    self.tag_and_length = ''
                    if length == 0:
                        # an empty frame carries no payload, wait for the next one
                        return
                    self.at_tlv_start_pos = False
                    self.length = length
            else:
                value = self.read_value()
                if value:
                    self.receiver.to_client_buffer += decrypt(value, self.key)
                    self.at_tlv_start_pos = True
                    self.value = ''
                    self.length = 0
                    self.frame_decoded()

    def handle_write(self):
        sent = self.send(self.receiver.from_client_buffer)
        logger.debug('write %04i to   %s:%d', sent, self.remote_ip, self.remote_port)
        self.receiver.from_client_buffer = self.receiver.from_client_buffer[sent:]
        self.flush_write()

    def handle_error(self):
        logger.exception('error on connection to %s:%d', self.remote_ip, self.remote_port)
        self.close_pair()

    def read_tag_and_length(self):
        tag_and_length_size = 3
        remain_size = tag_and_length_size - len(self.tag_and_length)
        if remain_size > 0:
            read = self.recv(remain_size)
            if read:
                logger.debug('read  %04i from %s:%d', len(read), self.remote_ip, self.remote_port)
                self.tag_and_length += read
                remain_size = tag_and_length_size - len(self.tag_and_length)
        if remain_size == 0:
            tag = struct.unpack('B', self.tag_and_length[0])[0]
            length = struct.unpack('!H', self.tag_and_length[1:3])[0]
            return tag, length
        return None, None

    def read_value(self):
        remain_size = self.length - len(self.value)
        if remain_size > 0:
            read = self.recv(remain_size)
            if read:
                logger.debug('read  %04i from %s:%d', len(read), self.remote_ip, self.remote_port)
                self.value += read
                remain_size = self.length - len(self.value)
        if remain_size == 0:
            return self.value


def parse_addr(addr):
    """Parse an 'address:port' pair. Return None when it is missing or malformed."""
    if not addr or addr.count(':') != 1:
        return None
    ip, port = addr.split(':')
    if not ip or not port.isdigit():
        return None
    port = int(port)
    if not 0 < port < 65536:
        return None
    return ip, port


def main():
    parser = optparse.OptionParser(version='0.1.0')
    parser.add_option('-m', '--mode', dest='mode', help='client, server')
    parser.add_option('-l', '--local', dest='local_addr', help='local address:port, eg: 127.0.0.1:8080')
    parser.add_option('-r', '--remote', dest='remote_addr', help='remote address:port, eg: 192.168.0.120:8080')
    parser.add_option('-k', '--key', dest='key', help='key, eg: helloworld')
    parser.add_option('-v', '--verbose', action='store_true', dest='verbose', help='verbose')
    opts, args = parser.parse_args()

    if len(sys.argv) == 1 or len(args) > 0:
        parser.print_help()
        sys.exit()

    local = parse_addr(opts.local_addr)
    remote = parse_addr(opts.remote_addr)

    opts_error = False
    if opts.mode not in ('client', 'server'):
        opts_error = True
    if not opts.key:
        opts_error = True
    if local is None or remote is None:
        opts_error = True

    if opts_error:
        parser.print_help()
        sys.exit()

    if opts.verbose:
        logging.disable(logging.NOTSET)
    else:
        logging.disable(logging.CRITICAL)

    local_ip, local_port = local
    remote_ip, remote_port = remote
    key = hashlib.sha1(opts.key).hexdigest()
    tunnel = PyTunnel(local_ip, local_port, remote_ip, remote_port, opts.mode, key)

    try:
        asyncore.loop(use_poll=True)
    except KeyboardInterrupt:
        print 'quit'
        sys.exit()


if __name__ == '__main__':
    main()
