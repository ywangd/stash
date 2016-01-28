# coding: utf-8
import os
import sys
import logging
import threading
from StringIO import StringIO

import pyparsing as pp

# Detecting environments
try:
    import ui
except ImportError:
    import system.dummyui as ui

from .shcommon import ShBadSubstitution, ShInternalError, ShIsDirectory, \
    ShFileNotFound, ShEventNotFound, ShNotExecutable
from .shcommon import _SYS_STDOUT, _SYS_STDERR, _SYS_PATH, _STASH_ROOT, _STASH_HISTORY_FILE
from .shcommon import is_binary_file
from .shthreads import ShTracedThread, ShCtypesThread, ShState, ShChildThreads


# Default .stashrc file
_DEFAULT_RC = r"""BIN_PATH=~/Documents/bin:$BIN_PATH
SELFUPDATE_BRANCH=master
PYTHONPATH=$STASH_ROOT/lib:$PYTHONPATH
alias env='printenv'
alias logout='echo "Use the close button in the upper right corner to exit StaSh."'
alias help='man'
alias la='ls -a'
alias ll='ls -la'
alias copy='pbcopy'
alias paste='pbpaste'
"""


class ShRuntime(object):

    """
    Runtime class responsible for parsing and executing commands.
    """

    def __init__(self, stash, parser, expander, debug=False):
        self.stash = stash
        self.parser = parser
        self.expander = expander
        self.debug = debug
        self.logger = logging.getLogger('StaSh.Runtime')

        # self.enclosed_envars = {}
        # self.enclosed_aliases = {}
        # self.enclosed_cwd = ''

        # self.envars = dict(os.environ,
        #                    HOME2=os.path.join(os.environ['HOME'], 'Documents'),
        #                    STASH_ROOT=_STASH_ROOT,
        #                    BIN_PATH=os.path.join(_STASH_ROOT, 'bin'),
        #                    PROMPT='[\W]$ ',
        #                    PYTHONISTA_ROOT=os.path.dirname(sys.executable))
        # self.aliases = {}

        config = stash.config
        self.rcfile = os.path.join(_STASH_ROOT, config.get('system', 'rcfile'))
        self.historyfile = os.path.join(_STASH_ROOT, _STASH_HISTORY_FILE)
        self.HISTORY_MAX = config.getint('display', 'HISTORY_MAX')

        self.py_traceback = config.getint('system', 'py_traceback')
        self.py_pdb = config.getint('system', 'py_pdb')
        self.input_encoding_utf8 = config.getint('system', 'input_encoding_utf8')
        self.ipython_style_history_search = config.getint('system', 'ipython_style_history_search')
        self.ShThread = {'traced': ShTracedThread, 'ctypes': ShCtypesThread}.get(
            config.get('system', 'thread_type'),
            ShCtypesThread
        )

        # load history from last session
        # NOTE the first entry in history is the latest one
        try:
            with open(self.historyfile) as ins:
                # History from old to new, history at 0 is the oldest
                self.history = [line.strip() for line in ins.readlines()]
        except IOError:
            self.history = []
        self.history_alt = []

        self.history_listsource = ui.ListDataSource(self.history)
        self.history_listsource.action = self.history_popover_tapped
        self.idx_to_history = -1
        self.history_templine = ''

        # self.enclosing_envars = {}
        # self.enclosing_aliases = {}
        # self.enclosing_cwd = ''
        #
        # self.state_stack = []
        # self.worker_stack = []

        self.state = ShState(
            envars=dict(os.environ,
                        HOME2=os.path.join(os.environ['HOME'], 'Documents'),
                        STASH_ROOT=_STASH_ROOT,
                        BIN_PATH=os.path.join(_STASH_ROOT, 'bin'),
                        PROMPT='[\W]$ ',
                        PYTHONISTA_ROOT=os.path.dirname(sys.executable))
        )
        self.child_threads = ShChildThreads()

    def save_state(self):

        if self.debug:
            self.logger.debug('Saving stack %d ----\n' % len(self.state_stack))
            self.logger.debug('envars = %s\n' % sorted(self.envars.keys()))

        self.state_stack.append(
            [dict(self.enclosed_envars),
             dict(self.enclosed_aliases),
             self.enclosed_cwd,
             sys.argv[:],
             dict(os.environ),
             sys.stdin,
             sys.stdout,
             sys.stderr,
            ])

        # new enclosed and enclosing variables
        self.enclosed_envars = dict(self.envars)
        self.enclosed_aliases = dict(self.aliases)
        self.enclosed_cwd = os.getcwd()

        # envars for next level shell is envars of current level plus all current enclosing
        if self.enclosing_envars:
            self.envars.update(self.enclosing_envars)
            self.enclosing_envars = {}

        if self.enclosing_aliases:
            self.aliases.update(self.enclosing_aliases)
            self.enclosing_aliases = {}

        if self.enclosing_cwd and self.enclosing_cwd != os.getcwd():
            os.chdir(self.enclosing_cwd)
            self.enclosing_cwd = ''

        if len(self.worker_stack) == 1:
            self.history, self.history_alt = self.history_alt, self.history

    def restore_state(self,
                      persist_envars=False,
                      persist_aliases=False,
                      persist_cwd=False):

        if self.debug:
            self.logger.debug('Popping stack %d ----\n' % (len(self.state_stack) - 1))
            self.logger.debug('envars = %s\n' % sorted(self.envars.keys()))

        if len(self.worker_stack) == 1:
            self.history, self.history_alt = self.history_alt, self.history

        # If not persisting, parent shell's envars are set back to this level's
        # enclosed vars. If persisting, envars of this level is then the same
        # as its parent's envars.
        self.enclosing_envars = self.envars
        if not (persist_envars or len(self.worker_stack) == 1):
            self.envars = self.enclosed_envars

        self.enclosing_aliases = self.aliases
        if not (persist_aliases or len(self.worker_stack) == 1):
            self.aliases = self.enclosed_aliases

        self.enclosing_cwd = os.getcwd()
        if not (persist_cwd or len(self.worker_stack) == 1):
            if os.getcwd() != self.enclosed_cwd:
                os.chdir(self.enclosed_cwd)

        (self.enclosed_envars,
         self.enclosed_aliases,
         self.enclosed_cwd,
         sys.argv,
         os.environ,
         sys.stdin,
         sys.stdout,
         sys.stderr) = self.state_stack.pop()

        if self.debug:
            self.logger.debug('After poping\n')
            self.logger.debug('enclosed_envars = %s\n' % sorted(self.enclosing_envars.keys()))
            self.logger.debug('envars = %s\n' % sorted(self.envars.keys()))

    def load_rcfile(self):
        self.stash(_DEFAULT_RC.splitlines(), add_to_history=False, add_new_inp_line=False)

        # TODO: NO RC FILE loading
        if os.path.exists(self.rcfile) and os.path.isfile(self.rcfile):
            try:
                with open(self.rcfile) as ins:
                    self.stash(ins.readlines(), add_to_history=False, add_new_inp_line=False)
            except IOError:
                self.stash.write_message('%s: error reading rcfile\n' % self.rcfile)

    def find_script_file(self, filename):
        dir_match_found = False
        # direct match of the filename, e.g. full path, relative path etc.
        for fname in (filename, filename + '.py', filename + '.sh'):
            if os.path.exists(fname):
                if os.path.isdir(fname):
                    dir_match_found = True
                else:
                    return fname

        # Match for commands in current dir and BIN_PATH
        # Effectively, current dir is always the first in BIN_PATH
        for path in ['.'] + self.envars['BIN_PATH'].split(':'):
            path = os.path.expanduser(path)
            if os.path.exists(path):
                for f in os.listdir(path):
                    if f == filename or f == filename + '.py' or f == filename + '.sh':
                        if os.path.isdir(f):
                            dir_match_found = True
                        else:
                            return os.path.join(path, f)
        if dir_match_found:
            raise ShIsDirectory('%s: is a directory' % filename)
        else:
            raise ShFileNotFound('%s: command not found' % filename)

    def get_all_script_names(self):
        """ This function used for completer, whitespaces in names are escaped"""
        all_names = []
        for path in ['.'] + self.envars['BIN_PATH'].split(':'):
            path = os.path.expanduser(path)
            if os.path.exists(path):
                for f in os.listdir(path):
                    if not os.path.isdir(f) and (f.endswith('.py') or f.endswith('.sh')):
                        all_names.append(f.replace(' ', '\\ '))
        return all_names

    def run(self, input_,
            final_ins=None,
            final_outs=None,
            final_errs=None,
            add_to_history=None,
            add_new_inp_line=None,
            persist_envars=False,
            persist_aliases=False,
            persist_cwd=False):

        # Ensure the linearity of the worker threads.
        # To spawn a new worker thread, it is either
        #   1. No previous worker thread
        #   2. The last worker thread in stack is the current running one
        if self.worker_stack and self.worker_stack[-1] != threading.currentThread():
            self.stash.write_message('worker threads must be linear\n')

        # noinspection PyDocstring
        def fn():
            self.worker_stack.append(threading.currentThread())

            try:
                if type(input_) is list:
                    lines = input_
                elif input_ == self.stash.io:
                    lines = self.stash.io.readline_no_block()
                else:
                    lines = input_.splitlines()

                for line in lines:
                    # Ignore empty lines
                    if line.strip() == '':
                        continue

                    # Parse and expand the line (note this function returns a generator object)
                    expanded = self.expander.expand(line)
                    # The first member is the history expanded form and number of pipe_sequence
                    newline, n_pipe_sequences = expanded.next()
                    # Only add history entry if:
                    #   1. It is explicitly required
                    #   2. It is the first layer thread directly spawned by the main thread
                    #      and not explicitly required to not add
                    if (add_to_history is None and len(self.worker_stack) == 1) or add_to_history:
                        self.add_history(newline)

                    # Subsequent members are actual commands
                    for _ in range(n_pipe_sequences):
                        self.save_state()  # State needs to be saved before expansion happens
                        try:
                            pipe_sequence = expanded.next()
                            if pipe_sequence.in_background:
                                ui.in_background(self.run_pipe_sequence)(pipe_sequence,
                                                                         final_ins=final_ins,
                                                                         final_outs=final_outs,
                                                                         final_errs=final_errs)
                            else:
                                self.run_pipe_sequence(pipe_sequence,
                                                       final_ins=final_ins,
                                                       final_outs=final_outs,
                                                       final_errs=final_errs)
                        finally:
                            self.restore_state(persist_envars=persist_envars,
                                               persist_aliases=persist_aliases,
                                               persist_cwd=persist_cwd)

            except pp.ParseException as e:
                if self.debug:
                    self.logger.debug('ParseException: %s\n' % repr(e))
                self.stash.write_message('syntax error: at char %d: %s\n' % (e.loc, e.pstr))

            except ShEventNotFound as e:
                if self.debug:
                    self.logger.debug('%s\n' % repr(e))
                self.stash.write_message('%s: event not found\n' % e.message)

            except ShBadSubstitution as e:
                if self.debug:
                    self.logger.debug('%s\n' % repr(e))
                self.stash.write_message('%s\n' % e.message)

            except ShInternalError as e:
                if self.debug:
                    self.logger.debug('%s\n' % repr(e))
                self.stash.write_message('%s\n' % e.message)

            except IOError as e:
                if self.debug:
                    self.logger.debug('IOError: %s\n' % repr(e))
                self.stash.write_message('%s: %s\n' % (e.filename, e.strerror))

            except KeyboardInterrupt as e:
                self.stash.write_message('^C\nKeyboardInterrupt: %s\n' % e.message)

            # This catch all exception handler is to handle errors outside of
            # run_pipe_sequence. The traceback print is mainly for debugging
            # the shell itself as opposed to the running script (handled inside
            # exec_py_file)
            except Exception as e:
                etype, evalue, tb = sys.exc_info()
                if self.debug:
                    self.logger.debug('Exception: %s\n' % repr(e))
                self.stash.write_message('%s\n' % repr(e))
                if self.py_traceback or self.py_pdb:
                    import traceback
                    traceback.print_exception(etype, evalue, tb)

            finally:
                if add_new_inp_line or (len(self.worker_stack) == 1 and add_new_inp_line is not False):
                    self.script_will_end()
                self.worker_stack.pop()  # remove itself from the stack

        worker = self.ShThread(target=fn)
        worker.start()
        return worker

    def run_by_user(self):
        self.run(self.stash.io)

    def script_will_end(self):
        self.stash.io.write(self.get_prompt(), no_wait=True)
        # Config the mini buffer so that user commands can be processed
        self.stash.mini_buffer.config_runtime_callback(self.run_by_user)
        # Reset any possible external tab handler setting
        self.stash.external_tab_handler = None

    def run_pipe_sequence(self, pipe_sequence, final_ins=None, final_outs=None, final_errs=None):
        if self.debug:
            self.logger.debug(str(pipe_sequence))

        n_simple_commands = len(pipe_sequence.lst)

        prev_outs = None
        for idx, simple_command in enumerate(pipe_sequence.lst):

            # The enclosing_envars needs to be reset for each simple command
            # i.e. A=42 script1 | script2
            # The value of A should not be carried to script2
            self.enclosing_envars = {}
            for assignment in simple_command.assignments:
                self.enclosing_envars[assignment.identifier] = assignment.value

            # Only update the runtime's env for pure assignments
            if simple_command.cmd_word == '' and idx == 0 and n_simple_commands == 1:
                self.envars.update(self.enclosing_envars)
                self.enclosing_envars = {}

            if prev_outs:
                if type(prev_outs) == file:
                    ins = StringIO()  # empty string
                else:
                    ins = prev_outs
            else:
                if final_ins:
                    ins = final_ins
                else:
                    ins = self.stash.io

            if not pipe_sequence.in_background:
                outs = self.stash.io
                errs = self.stash.io
            else:
                outs = _SYS_STDOUT
                errs = _SYS_STDERR

            if simple_command.io_redirect:
                mode = 'w' if simple_command.io_redirect.operator == '>' else 'a'
                # For simplicity, stdout redirect works for stderr as well.
                # Note this is different from a real shell.
                errs = outs = open(simple_command.io_redirect.filename, mode)

            elif idx < n_simple_commands - 1:  # before the last piped command
                outs = StringIO()

            else:
                if final_outs:
                    outs = final_outs
                if final_errs:
                    errs = final_errs

            if self.debug:
                self.logger.debug('io %s %s\n' % (ins, outs))

            try:
                if simple_command.cmd_word != '':
                    script_file = self.find_script_file(simple_command.cmd_word)

                    if self.debug:
                        self.logger.debug('script is %s\n' % script_file)

                    if self.input_encoding_utf8:
                        simple_command_args = [arg.encode('utf-8') for arg in simple_command.args]
                    else:
                        simple_command_args = simple_command.args

                    if script_file.endswith('.py'):
                        self.exec_py_file(script_file, simple_command_args, ins, outs, errs)

                    elif is_binary_file(script_file):
                        raise ShNotExecutable(script_file)

                    else:
                        self.exec_sh_file(script_file, simple_command_args, ins, outs, errs)

                else:
                    self.envars['?'] = 0

                if self.envars['?'] != 0:
                    break  # break out of the pipe_sequence, but NOT pipe_sequence list

                if isinstance(outs, StringIO):
                    outs.seek(0)  # rewind for next command in the pipe sequence

                prev_outs = outs

            # This catch all exception is for when the exception is raised
            # outside of the actual command execution, i.e. exec_py_file
            # exec_sh_file, e.g. command not found, not executable etc.
            except Exception as e:
                err_msg = '%s\n' % e.message
                if self.debug:
                    self.logger.debug(err_msg)
                self.stash.write_message(err_msg)
                break  # break out of the pipe_sequence, but NOT pipe_sequence list

            finally:
                if type(outs) is file:
                    outs.close()
                if isinstance(ins, StringIO):  # release the string buffer
                    ins.close()

    def exec_py_file(self, filename, args=None,
                     ins=None, outs=None, errs=None):
        if args is None:
            args = []

        sys.path = _SYS_PATH[:]
        # Add any user set python paths right after the dot or at the beginning
        if 'PYTHONPATH' in self.envars.keys():
            try:
                idxdot = sys.path.index('.') + 1
            except ValueError:
                idxdot = 0
            for pth in reversed(self.envars['PYTHONPATH'].split(':')):
                if pth == '':  # this for when existing PYTHONPATH is empty
                    continue
                pth = os.path.expanduser(pth)
                if pth not in sys.path:
                    sys.path.insert(idxdot, pth)

        try:
            if ins:
                sys.stdin = ins
            if outs:
                sys.stdout = outs
            if errs:
                sys.stderr = errs
            sys.argv = [os.path.basename(filename)] + args  # First argument is the script name
            os.environ = self.envars

            file_path = os.path.relpath(filename)
            namespace = dict(locals(), **globals())
            namespace['__name__'] = '__main__'
            namespace['__file__'] = os.path.abspath(file_path)
            namespace['_stash'] = self.stash
            execfile(file_path, namespace, namespace)
            self.envars['?'] = 0

        except SystemExit as e:
            self.envars['?'] = e.code

        except Exception as e:
            self.envars['?'] = 1
            etype, evalue, tb = sys.exc_info()
            err_msg = '%s: %s\n' % (repr(etype), evalue)
            if self.debug:
                self.logger.debug(err_msg)
            self.stash.write_message(err_msg)
            if self.py_traceback or self.py_pdb:
                import traceback
                traceback.print_exception(etype, evalue, tb)
                if self.py_pdb:
                    import pdb
                    pdb.post_mortem(tb)

        finally:
            sys.path = _SYS_PATH

    def exec_sh_file(self, filename, args=None,
                     ins=None, outs=None, errs=None,
                     add_to_history=None):
        if args is None:
            args = []
        try:
            for i, arg in enumerate([filename] + args):
                self.enclosing_envars[str(i)] = arg
            self.enclosing_envars['#'] = len(args)
            self.enclosing_envars['@'] = '\t'.join(args)

            with open(filename) as fins:
                worker = self.run(fins.readlines(),
                                  final_ins=ins,
                                  final_outs=outs,
                                  final_errs=errs,
                                  add_to_history=add_to_history,
                                  add_new_inp_line=False)
                worker.join()
            if '?' in self.enclosing_envars.keys():
                self.envars['?'] = self.enclosing_envars['?']
            else:
                self.envars['?'] = 0

        except IOError as e:
            self.stash.write_message('%s: %s\n' % (e.filename, e.strerror))
            self.envars['?'] = 1

        except:
            self.stash.write_message('%s: error while executing shell script\n' % filename)
            self.envars['?'] = 2

    def get_prompt(self):
        prompt = self.envars['PROMPT']
        if prompt.find('\\W') != -1 or prompt.find('\\w') != -1:
            curdir = os.getcwd().replace(self.envars['HOME'], '~')
            prompt = prompt.replace('\\w', curdir)
            prompt = prompt.replace('\\W',
                                    curdir if os.path.dirname(curdir) == '~'
                                    else os.path.basename(curdir))

        return self.stash.text_color(prompt, 'smoke')

    # TODO: The history stuff should be handled by a separate class
    def add_history(self, s):
        if s.strip() != '' and (self.history == [] or s != self.history[0]):
            self.history.insert(0, s.strip())  # remove any surrounding whites
            if len(self.history) > self.HISTORY_MAX:
                self.history = self.history[0:self.HISTORY_MAX]
            self.history_listsource.items = self.history
        self.reset_idx_to_history()

    def save_history(self):
        try:
            with open(self.historyfile, 'w') as outs:
                outs.write('\n'.join(self.history))
        except IOError:
            pass

    def search_history(self, tok):
        search_string = tok[1:]
        if search_string == '':
            return ''
        if search_string == '!':
            return self.history[0]
        try:
            idx = int(search_string)
            try:
                return self.history[::-1][idx]
            except IndexError:
                raise ShEventNotFound(tok)
        except ValueError:
            for entry in self.history:
                if entry.startswith(search_string):
                    return entry
            raise ShEventNotFound(tok)

    def history_up(self):
        # Save the unfinished line user is typing before showing entries from history
        if self.idx_to_history == -1:
            self.history_templine = self.stash.mini_buffer.modifiable_chars.rstrip()

        self.idx_to_history += 1
        if self.idx_to_history >= len(self.history):
            self.idx_to_history = len(self.history) - 1

        else:
            entry = self.history[self.idx_to_history]
            # If move up away from an unfinished input line, try search history for
            # a line starts with the unfinished line
            if self.idx_to_history == 0 and self.ipython_style_history_search:
                for idx, hs in enumerate(self.history):
                    if hs.startswith(self.history_templine):
                        entry = hs
                        self.idx_to_history = idx
                        break

            self.stash.mini_buffer.feed(None, entry)

    def history_dn(self):
        self.idx_to_history -= 1
        if self.idx_to_history < -1:
            self.idx_to_history = -1

        else:
            if self.idx_to_history == -1:
                entry = self.history_templine
            else:
                entry = self.history[self.idx_to_history]

            self.stash.mini_buffer.feed(None, entry)

    def reset_idx_to_history(self):
        self.idx_to_history = -1

    def history_popover_tapped(self, sender):
        if sender.selected_row >= 0:
            # Save the unfinished line user is typing before showing entries from history
            if self.idx_to_history == -1:
                self.history_templine = self.stash.mini_buffer.modifiable_chars.rstrip()
            self.stash.mini_buffer.feed(None, sender.items[sender.selected_row])
            self.idx_to_history = sender.selected_row
