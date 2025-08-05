# -*- coding: utf-8 -*-
"""Subprocess management"""
# info: parts of this module has been copied from the original subprocess-module

# === NotImplemented ===
# - the following args are always ignored:
# - executable
# - shell
# - startupinfo
# - preexec_fn
# - bufsize
# - creationflags
# - close_fds
# Other implemention differences:
# - terminate() is just a kill()
# - send_signal() always call kill()
# - communicate() splits data in chunks of 4096 bytes before sending
# - poll() never returns the signal that killed the process
# - pid is the job_id

import os
import select
import time
import sys
from mlpatches import base, l2c
from six import integer_types, string_types

_stash = base._stash
list2cmdline = l2c.list2cmdline

# constants
try:
    # setup MAXFD. we dont require this, but other scripts may expect this value to be present
    MAXFD = os.sysconf("SC_OPEN_MAX")
except:
    MAXFD = 256

PIPE = -1
STDOUT = -2


class CalledProcessError(Exception):
    """Exception raised when a process run by check_call() or check_output() returns a non-zero exit status."""

    def __init__(self, returncode, cmd, output=None):
        self.returncode = returncode
        self.cmd = cmd
        self.output = output

    def __str__(self):
        return "Command '{c}' returned non-zero exit status {s}".format(
            c=self.cmd, s=self.returncode
        )


def call(*args, **kwargs):
    """Run the command described by args. Wait for command to complete, then return the returncode attribute."""
    return Popen(*args, **kwargs).wait()


def check_call(*args, **kwargs):
    """Run command with arguments. Wait for command to complete. If the return code was zero then return, otherwise raise CalledProcessError. The CalledProcessError object will have the return code in the returncode attribute."""
    rc = call(*args, **kwargs)
    if rc != 0:
        cmd = kwargs.get("args")
        if cmd is None:
            cmd = args[0]
        raise CalledProcessError(rc, cmd)
    return 0


def check_output(*args, **kwargs):
    """Run command with arguments and return its output as a byte string.

    If the return code was non-zero it raises a CalledProcessError. The CalledProcessError object will have the return code in the returncode attribute and any output in the output attribute."""
    if "stdout" in kwargs:
        raise ValueError("stdout argument not allowed, it will be overriden.")
    p = Popen(stdout=PIPE, *args, **kwargs)
    out, _ = p.communicate()
    rc = p.poll()
    if rc != 0:
        cmd = kwargs.get("args")
        if cmd is None:
            cmd = args[0]
        raise CalledProcessError(rc, cmd, output=out)
    return out


class Popen(object):
    """Execute a child program in a new process. On Unix, the class uses os.execvp()-like behavior to execute the child program. On Windows, the class uses the Windows CreateProcess() function. The arguments to Popen are as follows."""

    def __init__(
        self,
        args,
        bufsize=0,
        executable=None,
        stdin=None,
        stdout=None,
        stderr=None,
        preexec_fn=None,
        close_fds=False,
        shell=False,
        cwd=None,
        env=None,
        universal_newlines=False,
        startupinfo=None,
        creationflags=None,
    ):
        # vars
        self._fds = []
        self.returncode = None
        self._worker = None
        self._cwd = cwd
        self._environ = env if env is not None else {}

        if isinstance(args, string_types):
            self.cmd = args
        else:
            if args[0] == sys.executable:
                # common use case
                args = ["python"] + list(args)[1:]
            self.cmd = l2c.list2cmdline(args)

        # === setup std* ===
        rfm = "r" if universal_newlines else "rb"
        # setup stdout
        if stdout is None:
            # use own stdout
            self.stdout = None
            self._sp_stdout = None
        elif stdout == PIPE:
            # create new pipe
            rfd, wfd = os.pipe()
            self._fds += [rfd, wfd]
            self.stdout = os.fdopen(rfd, rfm, bufsize)
            self._sp_stdout = os.fdopen(wfd, "wb")
        elif isinstance(stdout, integer_types):
            # use fd
            self.stdout = None
            self._fds.append(stdout)
            self._sp_stdout = os.fdopen(stdout, "wb")
        else:
            self.stdout = None
            self._sp_stdout = stdout

        # setup stderr
        if stderr is None:
            # use own stdout
            self.stderr = None
            self._sp_stderr = None
        elif stderr == PIPE:
            # create new pipe
            rfd, wfd = os.pipe()
            self._fds += [rfd, wfd]
            self.stderr = os.fdopen(rfd, rfm, bufsize)
            self._sp_stderr = os.fdopen(wfd, "wb")
        elif stderr == STDOUT:
            self.stderr = self.stdout
            self._sp_stderr = self._sp_stdout
        elif isinstance(stderr, integer_types):
            # use fd
            self.stderr = None
            self._fds.append(stderr)
            self._sp_stderr = os.fdopen(stderr, "wb")
        else:
            self.stderr = None
            self._sp_stderr = stderr

        # setup stdin
        if stdin is None:
            # use own stdin
            self.stdin = None
            self._sp_stdin = None
        elif stdin == PIPE:
            # create new pipe
            rfd, wfd = os.pipe()
            self._fds += [rfd, wfd]
            self.stdin = os.fdopen(wfd, "wb")
            self._sp_stdin = os.fdopen(rfd, "rb")
        elif isinstance(stdin, integer_types):
            # use fd
            self.stdin = None
            self._fds.append(stdin)
            self._sp_stdin = os.fdopen(stdin)
        else:
            self.stdin = None
            self._sp_stdin = stdin

        # run
        self._run()

    def __del__(self):
        """called on deletion"""
        try:
            self._close()
        except Exception as e:
            pass

    def _run(self):
        """creates and starts the worker."""
        self._worker = _stash.runtime.run(
            input_=self.cmd,
            final_ins=self._sp_stdin,
            final_outs=self._sp_stdout,
            final_errs=self._sp_stderr,
            add_to_history=None,
            persistent_level=2,
            is_background=False,
            cwd=self._cwd,
            environ=self._environ,
        )
        self.pid = self._worker.job_id

    def poll(self):
        """Check if child process has terminated. Set and return returncode attribute."""
        if self._worker is None:
            self.returncode = None
            return self.returncode
        elif self._worker.is_alive():
            self.returncode = None
            return self.returncode
        else:
            self.returncode = self._worker.state.return_value
            return self.returncode

    def wait(self):
        """Wait for child process to terminate. Set and return returncode attribute."""
        while self._worker is None:
            # wait() before self._run()
            time.sleep(0.1)
        self._worker.join()
        return self.poll()

    def terminate(self):
        """Stop the child. On Posix OSs the method sends SIGTERM to the child. On Windows the Win32 API function TerminateProcess() is called to stop the child."""
        self._worker.kill()

    kill = terminate

    def send_signal(self, signal):
        """Sends the signal signal to the child."""
        self.kill()

    def communicate(self, input=None):
        """Interact with process: Send data to stdin. Read data from stdout and stderr, until end-of-file is reached. Wait for process to terminate. The optional input argument should be a string to be sent to the child process, or None, if no data should be sent to the child."""
        rfs = []
        wfs = []
        ex = []
        if self.stdout is not None:
            stdoutdata = ""
            rfs.append(self.stdout)
        else:
            stdoutdata = None
        if self.stderr is self.stdout:
            seo = True
        else:
            seo = False
            if self.stderr is not None:
                stderrdata = ""
                rfs.append(self.stderr)
            else:
                stderrdata = None
        if (self.stdin is not None) and (input is not None):
            wfs.append(self.stdin)

        while len(rfs + wfs) > 0:
            tr, tw, he = select.select(rfs, wfs, ex)
            if self.stdin in tw:
                if len(input) < 4096:
                    self.stdin.write(input)
                    input = ""
                    wfs.remove(self.stdin)
                else:
                    self.stdin.write(input[:4096])
                    input = input[4096:]
            if self.stderr in tr:
                data = self.stderr.read(4096)
                if not data:
                    rfs.remove(self.stderr)
                else:
                    stderrdata += data
            if self.stdout in tr:
                data = self.stdout.read(4096)
                if not data:
                    rfs.remove(self.stdout)
                else:
                    stdoutdata += data

        if seo:
            return (stdoutdata, stdoutdata)
        else:
            return (stdoutdata, stderrdata)

    def _close(self):
        """close all fds and do other cleanup actions"""
        for fd in self._fds:
            try:
                os.close(fd)
            except:
                pass
