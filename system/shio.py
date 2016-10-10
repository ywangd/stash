# coding: utf-8
import logging
import time
from collections import deque


class ShIO(object):
    """
    The ShIO object is the read/write interface to users and running scripts.
    It acts as a staging area so that the UI Delegate calls can return without
    waiting for user read/write (no blocking on main thread).
    """

    def __init__(self, stash, debug=False):

        self.stash = stash
        self.debug = debug
        self.logger = logging.getLogger('StaSh.IO')
        self.tell_pos = 0
        # The input buffer, push from the Left end, read from the right end
        self._buffer = deque()
        self.chunk_size = 4096
        # When buffer is empty, hold back for certain before read again
        # This is to lower the cpu usage of the reading thread so it does
        # not affect the UI thread by noticeable amount
        self.holdback = 0.2

        self.encoding = 'utf8'

    def push(self, s):
        self._buffer.extendleft(s)

    # Following methods to provide file like object interface
    @property
    def closed(self):
        return False

    def isatty(self):
        return True

    def close(self):
        """
        This IO object cannot be closed.
        """
        pass

    def seek(self, offset):
        """
        Seek of stdout is not the real seek as file, it seems merely set
        the current posotion as the given parameter.
        :param offset:
        :return:
        """
        self.tell_pos = offset

    def tell(self):
        return self.tell_pos

    def truncate(self, size=None):
        """do nothing"""

    def read(self, size=-1):
        size = size if size != 0 else 1

        if size == -1:
            return ''.join(self._buffer.pop() for _ in len(self._buffer))

        else:
            ret = []
            while len(ret) < size:
                try:
                    ret.append(self._buffer.pop())
                except IndexError:
                    # Wait briefly when the buffer is empty to avoid taxing the CPU
                    time.sleep(self.holdback)

            return ''.join(ret)

    def readline(self, size=-1):
        ret = []
        while True:
            try:
                ret.append(self._buffer.pop())
                if ret[-1] in ['\n', '\0']:
                    break
            except IndexError:
                time.sleep(self.holdback)

        if ret[-1] == '\0':
            del ret[-1]

        line = ''.join(ret)
        # localized history for running scripts
        # TODO: Adding to history for read as well?
        self.stash.runtime.add_history(line)

        return line

    def readlines(self, size=-1):
        ret = []
        while True:
            try:
                ret.append(self._buffer.pop())
                if ret[-1] == '\0':
                    break
            except IndexError:
                time.sleep(self.holdback)

        ret = ''.join(ret[:-1])  # do not include the EOF

        if size != -1:
            ret = ret[:size]

        for line in ret.splitlines():
            self.stash.runtime.add_history(line)

        return ret.splitlines(True)

    def read1(self):
        """
        Put MiniBuffer in cbreak mode to process character by character.
        Normally the MiniBuffer only sends out its reading after a LF.
        With this method, MiniBuffer sends out its reading after every
        single char.
        The caller is responsible for break out this reading explicitly.
        """
        # TODO: Currently not supported by ShMiniBuffer
        try:
            self.stash.mini_buffer.cbreak = True
            while True:
                try:
                    yield self._buffer.pop()
                except IndexError:
                    time.sleep(self.holdback)

        finally:
            self.stash.mini_buffer.cbreak = False

    def readline_no_block(self):
        """
        Read lines from the buffer but does NOT wait till lines to be completed.
        If no complete line can be read, just return with None.
        This is useful for runtime to process multiple commands from user. The
        generator form also helps the program to keep reading and processing
        user command when a program is running at the same time.
        :return: str:
        """
        ret = []
        while True:
            try:
                ret.append(self._buffer.pop())
                if ret[-1] == '\n':
                    yield ''.join(ret)
                    ret = []
            except IndexError:
                self._buffer.extend(ret)
                break

    def write(self, s, no_wait=False):
        if len(s) == 0:  # skip empty string
            return
        idx = 0
        while True:
            self.stash.stream.feed(s[idx: idx + self.chunk_size], no_wait=no_wait)  # main screen only
            idx += self.chunk_size
            if idx >= len(s):
                break

    def writelines(self, s_list):
        self.write(''.join(s_list))

    def flush(self):
        pass
