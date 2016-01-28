# coding=utf-8
"""
Killable threads
"""
import os
import sys
import threading
import weakref
import ctypes

from .shcommon import M_64


class ShChildThreads(object):
    def __init__(self):
        self.fg_thread = None
        self.bg_threads = []

    def __iter__(self):
        return ([self.fg_thread] + self.bg_threads) if self.fg_thread else self.bg_threads

    def __len__(self):
        return len(self.bg_threads) + (1 if self.fg_thread else 0)



class ShState(object):
    def __init__(self, envars=None, aliases=None, enclosed_cwd=None):
        self.envars = envars or {}
        self.aliases = aliases or {}
        self.enclosed_cwd = enclosed_cwd
        self.sys_argv = sys.argv[:]
        self.os_environ = dict(os.environ)
        self.sys_stdin = sys.stdin
        self.sys_stdout = sys.stdout
        self.sys_stderr = sys.stderr

    @staticmethod
    def new_from_existing(state):
        return ShState(envars=dict(state.envars),
                       aliases=dict(state.aliases),
                       enclosed_cwd=os.getcwd())


class ShBaseThread(threading.Thread):
    def __init__(self, parent, target=None, verbose=None):
        super(ShBaseThread, self).__init__(group=None,
                                           target=target,
                                           name='_shthread',
                                           args=(),
                                           kwargs=None,
                                           verbose=verbose)

        self.parent = parent
        self.killed = False
        self.child_threads = ShChildThreads()
        self.state = ShState.new_from_existing(self.parent.state)

    def is_top_level(self):
        """
        Whether or not the thread is directly under the runtime, aka top level
        """
        return not isinstance(self.parent, ShBaseThread)


# noinspection PyAttributeOutsideInit
class ShTracedThread(ShBaseThread):
    """ Killable thread implementation with trace """

    def __init__(self, target=None, verbose=None):
        super(ShTracedThread, self).__init__(target=target, verbose=verbose)

    def start(self):
        """Start the thread."""
        self.__run_backup = self.run
        self.run = self.__run  # Force the Thread to install our trace.
        threading.Thread.start(self)

    def __run(self):
        """Hacked run function, which installs the trace."""
        sys.settrace(self.globaltrace)
        self.__run_backup()
        self.run = self.__run_backup

    def globaltrace(self, frame, why, arg):
        return self.localtrace if why == 'call' else None

    def localtrace(self, frame, why, arg):
        if self.killed:
            if why == 'line':
                for ct in self.child_threads:
                    ct.kill()
                raise KeyboardInterrupt()
        return self.localtrace

    def kill(self):
        self.killed = True


class ShCtypesThread(ShBaseThread):
    """
    A thread class that supports raising exception in the thread from
    another thread (with ctypes).
    """

    def __init__(self, target=None, verbose=None):
        super(ShCtypesThread, self).__init__(target=target, verbose=verbose)

    def _async_raise(self):
        tid = self.ident
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid) if M_64 else tid,
                                                         ctypes.py_object(KeyboardInterrupt))
        if res == 0:
            raise ValueError("invalid thread id")
        elif res != 1:
            # "if it returns a number greater than one, you're in trouble,
            # and you should call it again with exc=NULL to revert the effect"
            ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), 0)
            raise SystemError("PyThreadState_SetAsyncExc failed")

        return res

    def kill(self):
        if not self.killed:
            self.killed = True
            for ct in self.child_threads:
                ct.kill()
            try:
                res = self._async_raise()
            except (ValueError, SystemError):
                self.killed = False
