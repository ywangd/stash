# coding: utf-8
import sys
import os
import re
import time
import math
import argparse
import threading
from distutils.version import StrictVersion

try:
    import ui
except ImportError:
    import dummyui as ui

_stash = globals()['_stash']
""":type : StaSh"""

try:
    import pyte
except ImportError:
    _stash('pip install pyte 0.4.10')

import paramiko

if StrictVersion(paramiko.__version__) < StrictVersion('1.15'):
    # Install paramiko 1.16.0 to fix a bug with version < 1.15
    _stash('pip install paramiko 1.16.0')
    print 'Please restart Pythonista for changes to take full effect'
    sys.exit(0)


class StashSSH(object):
    def __init__(self):
        self.ssh_running = False
        font_width, font_height = ui.measure_string(
            'a',
            font=('Menlo-Regular', _stash.config.getint('display', 'TEXT_FONT_SIZE')))
        self.screen = pyte.screens.DiffScreen(
            int(_stash.ui.width / font_width),
            int(_stash.ui.height / font_height)
        )
        self.screen.dirty.clear()
        self.stream = pyte.Stream()
        self.stream.attach(self.screen)

    def connect(self, host='', passwd=None, port=22):
        print 'Connecting...'
        self.user, self.host = host.split('@')
        self.passwd = passwd
        self.port = port
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            print 'Looking for SSH keys...'
            self.ssh.connect(self.host,
                             username=self.user,
                             password=self.passwd,
                             port=self.port,
                             key_filename=self.find_ssh_keys())
        except:
            try:
                print 'No SSH key found. Trying password...'
                if self.passwd is None:
                    self.passwd = raw_input("Enter password:")

                self.ssh.connect(self.host,
                                 username=self.user,
                                 password=self.passwd,
                                 port=self.port)
            except:
                print '*Auth Error*'
                return False
        self.ssh_running = True
        return True

    def find_ssh_keys(self):
        ssh_dir = os.path.join(os.environ['STASH_ROOT'], '.ssh')
        return [os.path.join(ssh_dir, file) for file
                in os.listdir(ssh_dir) if '.' not in file]

    def stdout_thread(self):
        while self.ssh_running:
            if self.chan.recv_ready():
                rcv = self.chan.recv(1024)
                # noinspection PyTypeChecker
                self.stream.feed(u'%s' % rcv)
            if self.screen.dirty:
                self.screen.dirty.clear()
                self.update_screen()

    def update_screen(self):
        _stash.main_screen.intact_left_bound = 0

        nlines, ncolumns = self.screen.lines, self.screen.columns

        
        for item in reversed(self.screen.display):
            if str(item) != ' ' * ncolumns:
                break


        min_dirty_line_idx = min(self.screen.dirty)
        idx_char_dirty = ncolumns * min_dirty_line_idx

        nchars_stash_screen = _stash.main_screen.text_length

        if nchars - 1 >= idx_char_dirty:
            for idx in range(idx_char_dirty, nchars):
                idx_line, idx_column = idx / ncolumns, idx % ncolumns
                if idx_column != ncolumns - 1 \
                    and not _stash.renderer._same_style(_stash.main_screen._buffer[idx],
                            self.screen.buffer[idx_line][idx_column]):
                    _stash.main_screen.intact_right_bound = idx
                    break



        nlines_of_stash_screen = int(math.ceil(nchars / (ncolumns + 1)))

        if nlines_of_stash_screen - 1 >= min_dirty_line_idx:




    def single_exec(self, command):
        sin, sout, serr = self.ssh.exec_command(command)
        for line in sout.readlines():
            line = line.replace('\n', '')
        for line in serr.readlines():
            print line.replace('\n', '')
        self.exit()

    def interactive(self):
        self.chan = self.ssh.invoke_shell()
        self.chan.set_combine_stderr(True)
        t1 = threading.Thread(target=self.stdout_thread)
        t1.start()
        while True:
            if self.chan.send_ready():
                pass
        else:
            self.exit()

    def exit(self):
        self.ssh_running = False
        self.chan.close()
        self.ssh.close()


class TextViewDelegate(object):
    def __init__(self, ssh):
        self.ssh = ssh

    def textview_did_begin_editing(self, tv):
        _stash.terminal.is_editing = True

    def textview_did_end_editing(self, tv):
        _stash.terminal.is_editing = False

    def textview_should_change(self, tv, rng, replacement):
        self.ssh.chan.send(replacement)
        return False  # always false

    def textview_did_change(self, tv):
        pass

    def textview_did_change_selection(self, tv):
        pass


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--password', action='store', default=None,
                    help='Password for rsa/dsa key or password login')
    ap.add_argument('-p', '--port', action='store', default=22, type=int,
                    help='port for ssh default: 22')
    ap.add_argument('host', help='host ex. user@host.com')
    ap.add_argument('command', nargs='?', default=False,
                    help='Command to send as a quoted string')
    args = ap.parse_args()

    ssh = StashSSH()
    tv_delegate = TextViewDelegate(ssh)

    if ssh.connect(host=args.host, passwd=args.password, port=args.port):
        if args.command:
            ssh.single_exec(args.command)
        else:
            _stash.stream.feed(u'\u009bc', render_it=False)
            with _stash.user_action_proxy.config(tv_responder=tv_delegate):
                ssh.interactive()
    else:
        print 'Connection Failed'
