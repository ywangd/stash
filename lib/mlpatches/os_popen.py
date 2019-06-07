# -*- coding: utf-8 -*-
import os
import time
from mlpatches import base

_stash = base._stash


def _get_status(exitcode, killer=0):
    """
	calculates the exit status for a command.
	see the documentation of os.wait for info about this.
	"""
    return (exitcode * 256) + killer


class VoidIO(object):
    """no-op I/O"""

    def __init__(self):
        pass

    def write(self, *args):
        pass

    def writelines(self, *args):
        pass

    def read(self, *args):
        return ""

    def readline(self, *args):
        return ""

    def readlines(self, *args):
        return []

    def close(self):
        pass

    def flush(self):
        pass


class _PipeEndpoint(object):
    """this class represents a pipe endpoint."""

    def __init__(self, root, pipe):
        self.__root = root
        self.__pipe = pipe

    def __getattr__(self, name):
        """return attribute name of the pipe."""
        return getattr(self.__pipe, name)

    def __hasattr__(self, name):
        """checks wether the pioe has a attribute called name."""
        return hasattr(self.__pipe, name)

    def __repr__(self):
        """returns the representation of the pipe."""
        return repr(self.__pipe)

    def __del__(self):
        """called on deletion."""
        self.close()

    def close(self):
        """closes the pipe."""
        try:
            os.close(self.__pipe.fileno())
        except (OSError, IOError):
            pass
        ec = self.__root.get_exit_code(wait=True)
        if ec / 256 == 0:
            return None  # see os.popen
        else:
            return ec


class _PopenCmd(object):
    """This class handles the command processing."""
    # TODO: replace state mechanics with single bool and threading.Lock()
    STATE_INIT = "INIT"
    STATE_RUNNING = "RUNNING"
    STATE_FINISHED = "FINISHED"

    def __init__(self, cmd, mode, bufsize, shared_eo=False):
        self.cmd = cmd
        self.mode = mode
        self.bufsize = bufsize
        self.fds = []
        self.worker = None
        self.state = self.STATE_INIT
        self.shared_eo = shared_eo
        self.chinr, self.chinw = self.create_pipe(wbuf=bufsize)
        self.choutr, self.choutw = self.create_pipe(rbuf=bufsize)
        if shared_eo:
            self.cherrr, self.cherrw = self.choutr, self.choutw
        else:
            self.cherrr, self.cherrw = self.create_pipe(rbuf=bufsize)

    def get_pipes(self):
        """returns the pipes."""
        if not self.shared_eo:
            return (_PipeEndpoint(self, self.chinw), _PipeEndpoint(self, self.choutr), _PipeEndpoint(self, self.cherrr))
        else:
            return (_PipeEndpoint(self, self.chinw), _PipeEndpoint(self, self.choutr))

    def close_fds(self):
        """close all fds."""
        for fd in self.fds:
            try:
                os.close(fd)
            except os.OSError:
                pass

    def create_pipe(self, rbuf=0, wbuf=0):
        """creates a pipe. returns (readpipe, writepipe)"""
        rfd, wfd = os.pipe()
        self.fds += [rfd, wfd]
        rf, wf = os.fdopen(rfd, "rb", rbuf), os.fdopen(wfd, "wb", wbuf)
        return rf, wf

    def run(self):
        """runs the command."""
        self.state = self.STATE_RUNNING
        self.worker = _stash.runtime.run(
            input_=self.cmd,
            persistent_level=2,
            is_background=False,
            add_to_history=False,
            final_ins=self.chinr,
            final_outs=self.choutw,
            final_errs=self.cherrw
        )
        if not self.worker.is_alive():
            # sometimes stash is faster than the return
            self.state = self.STATE_FINISHED

    def get_exit_code(self, wait=True):
        """returns the exitcode.
		If wait is False and the worker has not finishef yet, return None."""
        if self.state != self.STATE_INIT:
            if self.worker is None:
                # temp fix for pipes for fast commands
                if not wait:
                    return 0
                while self.worker is None:
                    time.sleep(0.01)
            if wait and self.worker.is_alive():
                self.worker.join()
                self.state = self.STATE_FINISHED
            elif self.worker.status() != self.worker.STOPPED:
                return None
            es = self.worker.state.return_value
            return _get_status(es, self.worker.killer)
        raise RuntimeError("get_exit_code() called before run()!")


def popen(patch, cmd, mode="r", bufsize=0):
    """Open a pipe to or from command. The return value is an open file object connected to the pipe, which can be read or written depending on whether mode is 'r' (default) or 'w'. The bufsize argument has the same meaning as the corresponding argument to the built-in open() function. The exit status of the command (encoded in the format specified for wait()) is available as the return value of the close() method of the file object, except that when the exit status is zero (termination without errors), None is returned."""
    cmd = _PopenCmd(cmd, mode, bufsize, shared_eo=False)
    pipes = cmd.get_pipes()
    cmd.run()
    if mode == "r":
        return pipes[1]
    elif mode == "w":
        return pipes[0]


def popen2(patch, cmd, mode="r", bufsize=0):
    """Execute cmd as a sub-process and return the file objects (child_stdin, child_stdout)."""
    cmd = _PopenCmd(cmd, mode, bufsize, shared_eo=False)
    pipes = cmd.get_pipes()
    cmd.run()
    return pipes[0], pipes[1]


def popen3(patch, cmd, mode="r", bufsize=0):
    """Execute cmd as a sub-process and return the file objects (child_stdin, child_stdout, child_stderr)."""
    cmd = _PopenCmd(cmd, mode, bufsize, shared_eo=False)
    pipes = cmd.get_pipes()
    cmd.run()
    return pipes[0], pipes[1], pipes[2]


def popen4(patch, cmd, mode="r", bufsize=0):
    """Execute cmd as a sub-process and return the file objects (child_stdin, child_stdout_and_stderr)."""
    cmd = _PopenCmd(cmd, mode, bufsize, shared_eo=True)
    pipes = cmd.get_pipes()
    cmd.run()
    return pipes[0], pipes[1]


def system(patch, command):
    """Execute the command (a string) in a subshell. This is implemented by calling the Standard C function system(), and has the same limitations. Changes to sys.stdin, etc. are not reflected in the environment of the executed command.

On Unix, the return value is the exit status of the process encoded in the format specified for wait(). Note that POSIX does not specify the meaning of the return value of the C system() function, so the return value of the Python function is system-dependent.

On Windows, the return value is that returned by the system shell after running command, given by the Windows environment variable COMSPEC: on command.com systems (Windows 95, 98 and ME) this is always 0; on cmd.exe systems (Windows NT, 2000 and XP) this is the exit status of the command run; on systems using a non-native shell, consult your shell documentation.

The subprocess module provides more powerful facilities for spawning new processes and retrieving their results; using that module is preferable to using this function. See the Replacing Older Functions with the subprocess Module section in the subprocess documentation for some helpful recipes."""
    io = VoidIO()
    worker = _stash.runtime.run(
        input_=command,
        persistent_level=2,
        is_background=False,
        add_to_history=False,
        final_ins=io,
        final_outs=io,
        final_errs=io,
    )
    worker.join()  # wait for completion
    es = worker.state.return_value
    return _get_status(es, worker.killer)
