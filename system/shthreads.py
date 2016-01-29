# coding=utf-8
"""
Killable threads
"""
import os
import sys
import threading
import weakref
import ctypes
from collections import OrderedDict

from .shcommon import M_64


class ShWorkerRegistry(object):
    """ Bookkeeping for all worker threads (both foreground and background).
    This is useful to provide an overview of all running threads.
    """

    def __init__(self):
        self.registry = OrderedDict()
        self._count = 1
        self._lock = threading.Lock()

    def _get_job_id(self):
        try:
            self._lock.acquire()
            job_id = self._count
            self._count += 1
            return job_id
        finally:
            self._lock.release()

    def add_worker(self, worker):
        worker.job_id = self._get_job_id()
        self.registry[worker.job_id] = worker

    def remove_worker(self, worker):
        self.registry.pop(worker.job_id)


class ShState(object):
    """ State of the current worker thread
    """
    def __init__(self,
                 envars=None,
                 aliases=None,
                 enclosed_cwd=None,
                 os_environ=None,
                 sys_argv=None,
                 sys_stdin=None,
                 sys_stdout=None,
                 sys_stderr=None):

        self.envars = envars or {}
        self.aliases = aliases or {}
        self.enclosed_cwd = enclosed_cwd
        self.os_environ = os_environ or dict(os.environ)
        self.sys_argv = sys_argv or sys.argv[:]
        self.sys_stdin = sys_stdin or sys.stdin
        self.sys_stdout = sys_stdout or sys.stdout
        self.sys_stderr = sys_stderr or sys.stderr

        self.enclosing_envars = {}

    @staticmethod
    def new_from_existing(state):
        envars = dict(state.envars)
        envars.update(state.enclosing_envars)
        return ShState(envars=envars,
                       aliases=dict(state.aliases),
                       enclosed_cwd=os.getcwd(),
                       os_environ=dict(state.os_environ),
                       sys_argv=state.sys_argv[:],
                       sys_stdin=state.sys_stdin,
                       sys_stdout=state.sys_stdout,
                       sys_stderr=state.sys_stderr)


class ShBaseThread(threading.Thread):
    """ The basic Thread class provides life cycle management.
    """
    def __init__(self, registry, parent, target=None, verbose=None):
        super(ShBaseThread, self).__init__(group=None,
                                           target=target,
                                           name='_shthread',
                                           args=(),
                                           kwargs=None,
                                           verbose=verbose)

        # Registry management
        self.registry = weakref.proxy(registry)
        self.job_id = None  # to be set by the registry
        registry.add_worker(self)

        # Set up the parent/child relationship
        if parent:
            assert parent.child_thread is None, 'parent must have no existing child thread'
            self.parent, parent.child_thread = weakref.proxy(parent), self
        else:  # background worker has no parent
            self.parent = None

        # Set up the state based on parent's state
        self.state = ShState.new_from_existing(parent.state)

        self.killed = False
        self.child_thread = None

    def is_top_level(self):
        """
        Whether or not the thread is directly under the runtime, aka top level
        """
        return not isinstance(self.parent, ShBaseThread)

    def cleanup(self):
        """
        End of life cycle management by remove itself from registry and unlink
        it self from parent if exists.
        """
        self.registry.remove_worker(self)
        if self.parent:
            assert self.parent.child_thread is self
            self.parent.child_thread = None


# noinspection PyAttributeOutsideInit
class ShTracedThread(ShBaseThread):
    """ Killable thread implementation with trace """

    def __init__(self, registry, parent, target=None, verbose=None):
        super(ShTracedThread, self).__init__(registry, parent, target=target, verbose=verbose)

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
                if self.child_thread:
                    self.child_thread.kill()
                raise KeyboardInterrupt()
        return self.localtrace

    def kill(self):
        self.killed = True


class ShCtypesThread(ShBaseThread):
    """
    A thread class that supports raising exception in the thread from
    another thread (with ctypes).
    """

    def __init__(self, registry, parent, target=None, verbose=None):
        super(ShCtypesThread, self).__init__(registry, parent, target=target, verbose=verbose)

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
            if self.child_thread:
                self.child_thread.kill()
            try:
                res = self._async_raise()
            except (ValueError, SystemError):
                self.killed = False



import imp
import __builtin__

mocksys = imp.new_module('sys')
_mocksys_code = """
from sys import *
asdf = 'HERE'
"""
exec _mocksys_code in mocksys.__dict__

mockos = imp.new_module('os')
_mockos_code = """
from os import *
asdf = 'HERE'
"""
exec _mockos_code in mockos.__dict__

mocks = {
    'sys': mocksys,
    'os': mockos,
}


intercept_modules = ('os', 'sys')

if not hasattr(__builtin__, '__baseimport'):
    __builtin__.__baseimport = __builtin__.__import__
    __builtin__.__basereload = __builtin__.reload

# noinspection PyUnresolvedReferences
__baseimport = __builtin__.__baseimport
# noinspection PyUnresolvedReferences
__basereload = __builtin__.__basereload


def __shimport(name, *args, **kwargs):
    print 'running through my import: %s' % name
    if name in intercept_modules \
            and isinstance(threading.currentThread(), ShBaseThread):
        print 'returning mock ...'
        return mocks[name]
    else:
        return __baseimport(name, *args, **kwargs)


def __shreload(m):
    print 'running through my reload: %s' % m
    if m.__name__ in intercept_modules\
            and isinstance(threading.currentThread(), ShBaseThread):
        print 'returning mock ...'
        return mocks[m.__name__]
    else:
        return __basereload(m)

__builtin__.__import__ = __shimport
__builtin__.reload = __shreload
