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
sys.stidin: {}
sys.stdout: {}
sys.stderr: {}
enclosing_environ: {}
environ: {}
"""


class ShState(object):
    """ State of the current worker thread
    """
    def __init__(self,
                 aliases=None,
                 environ=None,
                 enclosed_cwd=None,
                 sys_stdin=None,
                 sys_stdout=None,
                 sys_stderr=None,
                 sys_path=None):

        self.aliases = aliases or {}
        self.environ = environ or {}
        self.enclosed_cwd = enclosed_cwd

        self.sys_stdin__ = self.sys_stdin = sys_stdin or sys.stdin
        self.sys_stdout__ = self.sys_stdout = sys_stdout or sys.stdout
        self.sys_stderr__ = self.sys_stderr = sys_stderr or sys.stderr
        self.sys_path = sys_path or sys.path[:]

        self.enclosing_environ = {}

    def __str__(self):
        s = _STATE_STR_TEMPLATE.format(self.enclosed_cwd,
                                       self.aliases,
                                       self.sys_stdin,
                                       self.sys_stdout,
                                       self.sys_stderr,
                                       self.enclosing_environ,
                                       self.environ)
        return s

    @property
    def return_value(self):
        return self.environ.get('?', 0)

    @return_value.setter
    def return_value(self, value):
        self.environ['?'] = value

    def environ_get(self, name):
        return self.environ[name]

    def environ_set(self, name, value):
        self.environ[name] = value

    def copy(self, state):
        """
        This is used to carry child shell state to its parent shell
        :param ShState state: Other state
        """
        self.aliases = dict(state.aliases)
        self.enclosed_cwd = os.getcwd()
        self.environ = dict(state.environ)
        self.sys_path = state.sys_path[:]

    @staticmethod
    def new_from_parent(state):
        """
        Create new state from parent state. Parent's enclosing environ are merged as
        part of child's environ
        :param state:
        :return:
        """
        environ = dict(state.environ)
        environ.update(state.enclosing_environ)
        return ShState(aliases=dict(state.aliases),
                       environ=environ,
                       enclosed_cwd=os.getcwd(),
                       sys_stdin=state.sys_stdin__,
                       sys_stdout=state.sys_stdout__,
                       sys_stderr=state.sys_stderr__,
                       sys_path=state.sys_path[:])


class ShWorkerRegistry(object):
    """ Bookkeeping for all worker threads (both foreground and background).
    This is useful to provide an overview of all running threads.
    """

    def __init__(self):
        self.registry = OrderedDict()
        self._count = 1
        self._lock = threading.Lock()

    def __repr__(self):
        ret = []
        for job_id, thread in self.registry.items():
            ret.append('{:>5d}  {}'.format(job_id, thread))
        return '\n'.join(ret)

    def __iter__(self):
        return self.registry.values().__iter__()

    def __len__(self):
        return len(self.registry)

    def __contains__(self, item):
        return item in self.registry

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

    def get_worker(self, job_id):
        return self.registry.get(job_id, None)

    def get_first_bg_worker(self):
        for worker in self.registry.values():
            if worker.is_background:
                return worker
        else:
            return None

    def purge(self):
        """
        Kill all registered thread and clear the entire registry
        :return:
        """
        for worker in self.registry.values():
            worker.kill()
        # The worker removes itself from the registry when killed.


class ShBaseThread(threading.Thread):
    """ The basic Thread class provides life cycle management.
    """

    CREATED = 1
    STARTED = 2
    STOPPED = 3

    def __init__(self, registry, parent, command, target=None):
        super(ShBaseThread, self).__init__(group=None,
                                           target=target,
                                           name='_shthread',
                                           args=(),
                                           kwargs=None)

        # Registry management
        self.registry = weakref.proxy(registry)
        self.job_id = None  # to be set by the registry
        registry.add_worker(self)

        # The command that the thread runs
        if command.__class__.__name__ == 'ShIO':
            self.command = ''.join(command._buffer)[::-1].strip()
        else:
            self.command = command

        self.is_background = False

        assert parent.child_thread is None, 'spawning child thread from a busy parent'
        self.parent, parent.child_thread = weakref.proxy(parent), self

        # Set up the state based on parent's state
        self.state = ShState.new_from_parent(parent.state)

        self.killed = False
        self.child_thread = None

    def __repr__(self):
        command_str = str(self.command)
        return '[{}] {} {}'.format(
            self.job_id,
            {self.CREATED: 'Created', self.STARTED: 'Started', self.STOPPED: 'Stopped'}[self.status()],
            command_str[:20] + ('...' if len(command_str) > 20 else ''))

    def status(self):
        """
        Status of the thread. Created, Started or Stopped.
        """
        if self.isAlive():
            return self.STARTED
        elif self._Thread__stopped:
            return self.STOPPED
        else:
            return self.CREATED

    def set_background(self, is_background=True):
        self.is_background = is_background
        if is_background:
            if self.parent.child_thread is self:
                self.parent.child_thread = None
        else:
            assert self.parent.child_thread is None, 'parent must have no existing child thread'
            self.parent.child_thread = self

    def is_top_level(self):
        """
        Whether or not the thread is directly under the runtime, aka top level.
        A top level thread has the runtime as its parent
        """
        return not isinstance(self.parent, ShBaseThread) and not self.is_background

    def cleanup(self):
        """
        End of life cycle management by remove itself from registry and unlink
        it self from parent if exists.
        """
        self.registry.remove_worker(self)
        if not self.is_background:
            assert self.parent.child_thread is self
            self.parent.child_thread = None


# noinspection PyAttributeOutsideInit
class ShTracedThread(ShBaseThread):
    """ Killable thread implementation with trace """

    def __init__(self, registry, parent, command, target=None):
        super(ShTracedThread, self).__init__(
            registry, parent, command, target=target)

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

    def __init__(self, registry, parent, command, target=None):
        super(ShCtypesThread, self).__init__(
            registry, parent, command, target=target)

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

