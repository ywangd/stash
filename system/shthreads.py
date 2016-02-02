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

_STATE_STR_TEMPLATE = """enclosed_cwd: {}
aliases: {}
sys.argv: {}
sys.stidin: {}
sys.stdout: {}
sys.stderr: {}
enclosing_environ: {}
sys.path: {}
os.environ: {}
"""


class ShState(object):
    """ State of the current worker thread
    """
    def __init__(self,
                 aliases=None,
                 enclosed_cwd=None,
                 os_environ=None,
                 sys_argv=None,
                 sys_path=None,
                 sys_stdin=None,
                 sys_stdout=None,
                 sys_stderr=None):

        self.aliases = aliases or {}
        self.enclosed_cwd = enclosed_cwd

        self.os = {
            'environ': os_environ or dict(os.environ),
        }
        self.sys = {
            'argv': sys_argv or sys.argv[:],
            'path': sys_path or sys.path[:],
            'stdin': sys_stdin or sys.stdin,
            'stdout': sys_stdout or sys.stdout,
            'stderr': sys_stderr or sys.stderr,
        }
        self.enclosing_environ = {}

    def __str__(self):
        s = _STATE_STR_TEMPLATE.format(self.enclosed_cwd,
                                       self.aliases,
                                       self.sys['argv'],
                                       self.sys['stdin'],
                                       self.sys['stdout'],
                                       self.sys['stderr'],
                                       self.enclosing_environ,
                                       self.sys['path'],
                                       self.os['environ'])
        return s


    @property
    def return_value(self):
        return self.os['environ'].get('?', 0)

    @return_value.setter
    def return_value(self, value):
        self.os['environ']['?'] = value

    def environ_get(self, name):
        return self.os['environ'][name]

    def environ_set(self, name, value):
        self.os['environ'][name] = value

    def enable_enclosing_environ(self):
        if self.enclosing_environ:
            self.os['environ'].update(self.enclosing_environ)

    def disable_enclosing_environ(self):
        for k in self.enclosing_environ.keys():
            try:
                self.os['environ'].pop(k)
            except KeyError:  # ignore any error
                pass

    def copy(self, state):
        """

        :param ShState state: Other state
        :return:
        """
        self.aliases = state.aliases
        self.enclosed_cwd = os.getcwd()
        self.os.update(state.os)
        self.sys.update(state.sys)

    @staticmethod
    def new_from_parent(state):
        """
        Create new state from parent state. Parent's enclosing environ are merged as
        part of child's environ
        :param state:
        :return:
        """
        environ = dict(state.os['environ'])
        environ.update(state.enclosing_environ)
        return ShState(aliases=dict(state.aliases),
                       enclosed_cwd=os.getcwd(),
                       os_environ=environ,
                       sys_argv=state.sys['argv'][:],
                       sys_path=state.sys['path'][:],
                       sys_stdin=state.sys['stdin'],
                       sys_stdout=state.sys['stdout'],
                       sys_stderr=state.sys['stderr'])


class ShWorkerRegistry(object):
    """ Bookkeeping for all worker threads (both foreground and background).
    This is useful to provide an overview of all running threads.
    """

    def __init__(self):
        self.registry = OrderedDict()
        self._count = 1
        self._lock = threading.Lock()

    def __iter__(self):
        return self.registry.values()

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

    def purge(self):
        """
        Kill all registered thread and clear the entire registry
        :return:
        """
        for worker in self.registry.values():
            worker.kill()
        self.registry.clear()


class ShBaseThread(threading.Thread):
    """ The basic Thread class provides life cycle management.
    """
    def __init__(self, registry, parent, target=None, background=False, verbose=None):
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
        if not background:
            assert parent.child_thread is None, 'parent must have no existing child thread'
            self.parent, parent.child_thread = weakref.proxy(parent), self
        else:  # background worker does not need parent
            self.parent = None

        # Set up the state based on parent's state
        self.state = ShState.new_from_parent(parent.state)

        self.killed = False
        self.child_thread = None

        self.mock_modules = {}

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

    def __init__(self, registry, parent, target=None, background=False, verbose=None):
        super(ShTracedThread, self).__init__(
            registry, parent, target=target,  background=background, verbose=verbose)

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

    def __init__(self, registry, parent, target=None, background=False, verbose=None):
        super(ShCtypesThread, self).__init__(
            registry, parent, target=target, background=background, verbose=verbose)

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

