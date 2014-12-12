"""
Docstring
"""
__version__ = '0.1.0'

import os
import sys
from ConfigParser import ConfigParser
from StringIO import StringIO
import time
import threading
import glob
import contextlib
import functools

import pyparsing as pp

try:
    import ui
    _IN_PYTHONISTA = True
except:
    _IN_PYTHONISTA = False

# TODO:
#   history search in bang action using basic parser
#   auto-completes for "ls Script\ "
#   Allow external script to register callbacks for UI actions, e.g. button tap, input return
#   Disable Tab, history when a script is running
#   Stub ui for testing on PC
#   More buttons for symbols
#   Allow running scripts have full control over input textfields and maintains its own history and tab?
#
#   Object pickle not working properly (DropboxSync)
#
#   Bang command history expand
#   History with bang
#   More useful button (composite buttons?)
#   sys.exc information stack
#   review how outs is set
#
#   Documentation
#   Path/directory completion should have no trailing space


_STDIN = sys.stdin
_STDOUT = sys.stdout
_STDERR = sys.stderr


_DEBUG = False
_DEBUG_PARSER = False
_DEBUG_COMPLETER = False


APP_DIR = os.path.abspath(os.path.dirname(__file__))


class ShReprocess(Exception):
    pass

class ShFileNotFound(Exception):
    pass

class ShIsDirectory(Exception):
    pass

class ShTimeout(Exception):
    pass


def sh_delay(func, nseconds):
    t = threading.Timer(nseconds, func)
    t.start()
    return t

def sh_background(name=None):
    def wrap(func):
        @functools.wraps(func)
        def wrapped_func(*args, **kwargs):
            t = threading.Thread(name=name, target=func, args=args, kwargs=kwargs)
            t.start()
            return t
        return wrapped_func
    return wrap


_DEFAULT_RC = r"""
PROMPT='[\W]$ '
BIN_PATH=~/Documents/bin:$BIN_PATH
SELFUPDATE_BRANCH=master
alias la='ls -a'
alias ll='ls -la'
"""


class ShRuntime(object):

    def __init__(self, app=None):

        self.app = app
        self.envars = dict(os.environ,
                           HOME2=os.path.join(os.environ['HOME'], 'Documents'),
                           STASH_ROOT=APP_DIR,
                           BIN_PATH=os.path.join(APP_DIR, 'bin'))
        self.aliases = {}
        if app:
            config = app.config
            self.rcfile = os.path.join(APP_DIR, config.get('system', 'rcfile'))
            self.historyfile = os.path.join(APP_DIR, config.get('system', 'historyfile'))
            self.HISTORY_MAX = config.getint('display', 'HISTORY_MAX')
        else:
            self.rcfile = ''
            self.historyfile = ''
            self.HISTORY_MAX = 30

        # load history from last session
        # NOTE the first entry in history is the latest one
        try:
            with open(self.historyfile) as ins:
                # History from old to new, history at 0 is the oldest
                self.history = [line.strip() for line in ins.readlines()]
        except IOError:
            self.history = []
        self.history_listsource = ui.ListDataSource(self.history)
        self.history_listsource.action = self.app.history_popover_tapped
        self.idx_to_history = -1

        self.parser = ShParser(self)
        self.retval = 0
        self.state_stack = []
        self.worker_stack = []

    @contextlib.contextmanager
    def save_state(self):
        self.state_stack.append([sys.stdin,
                                 sys.stdout,
                                 sys.stderr,
                                 sys.argv[:],
                                 sys.path[:],
                                 dict(os.environ),
                                 ])
        try:
            yield
        finally:
            self.restore_state()

    def restore_state(self):
        (sys.stdin,
        sys.stdout,
        sys.stderr,
        sys.argv,
        sys.path,
        os.environ) = self.state_stack.pop()

    def load_rcfile(self):
        for line in _DEFAULT_RC.splitlines():
            if line.strip() != '':
                # Do not reset input as PROMPT variable may not set before rcfile is loaded
                worker = self.run(line.strip(), add_to_history=False, reset_inp=False)
                while worker.isAlive():
                    pass
        # Source rcfile
        try:
            self.exec_sh_file(self.rcfile)
        except IOError:
            #self.app.term.write_with_prefix('%s: rcfile does not exist\n' % self.rcfile)
            pass

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
        for path in ['.'] + self.envars['BIN_PATH'].split(os.pathsep):
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
        """ This function used for completer """
        all_names = []
        for path in ['.'] + self.envars['BIN_PATH'].split(os.pathsep):
            path = os.path.expanduser(path)
            if os.path.exists(path):
                for f in os.listdir(path):
                    if not os.path.isdir(f) and (f.endswith('.py') or f.endswith('.sh')):
                        all_names.append(f)
        return all_names

    # This method is for normal flow of command execution.
    # It updates the terminal and environment normally
    def run(self, line, final_outs=None, add_to_history=True,
            update_env=True,
            code_validation_func=None,
            reset_inp=True):

        return self.callback_run(line, final_outs=final_outs,
                                 add_to_history=add_to_history,
                                 update_env=update_env,
                                 code_validation_func=code_validation_func,
                                 reset_inp=reset_inp)

    # The callback run is for callback to the runtime when inside a
    # running thread of the runtime. Commands executed via callback
    # normally does not want update the environment (as if it is in
    # a sub-shell) and does not reset on terminal.
    # The code_validation_func is to be used by an external script
    # to provide security check on user-supplied arguments.
    def callback_run(self, line, final_outs=None, add_to_history=False,
                     update_env=False,
                     code_validation_func=None,
                     reset_inp=False):

        # Ensure the linearity of the worker threads.
        # To spawn a new worker thread, it is either
        #   1. No previous worker thread
        #   2. The last worker thread in stack is the current running one
        if self.worker_stack and self.worker_stack[-1] != threading.currentThread():
            self.app.term.write_with_prefix('worker threads must be linear\n')

        def fn():
            try:
                complete_command = self.parser.parse(line)
                if add_to_history:
                    self.add_history(line)
                if code_validation_func is None or code_validation_func(complete_command):
                    self.run_complete_command(complete_command,
                                              final_outs=final_outs,
                                              update_env=update_env)
            except pp.ParseException as e:
                if _DEBUG_PARSER:
                    _STDOUT.write('ParseException: %s\n' % repr(e))
                if self.app:
                    self.app.term.write_with_prefix('parsing error: at char %d: %s\n' % (e.loc, e.pstr))

            except IOError as e:
                if _DEBUG:
                    _STDOUT.write('IOError: %s\n' % repr(e))
                if self.app:
                    self.app.term.write_with_prefix('%s: %s\n' % (e.filename, e.strerror))

            except Exception as e:
                if _DEBUG:
                    _STDOUT.write('Exception: %s\n' % repr(e))
                if self.app:
                    self.app.term.write_with_prefix('%s\n' % repr(e))

            finally:
                self.worker_stack.pop()  # remove itself from the stack
                if self.app:
                    if reset_inp:
                        self.app.term.reset_inp()
                    self.app.term.flush()

        worker = threading.Thread(name='_shruntime_thread', target=fn)
        self.worker_stack.append(worker)
        worker.start()
        return worker

    def run_complete_command(self, complete_command, final_outs=None, update_env=True):

        for pipeline in complete_command.pipeline_list:
            if _DEBUG:
                print pipeline

            n_simple_commands = len(pipeline.pipe_sequence)

            prev_outs = None
            for idx, simple_command in enumerate(pipeline.pipe_sequence):
                new_envars = {}
                for assignment in simple_command.assignments:
                    new_envars[assignment.identifier] = assignment.value

                # Only update the runtime's env for pure assignments
                if update_env and simple_command.cmd_word == '' and idx == 0 and n_simple_commands == 1:
                    self.envars.update(new_envars)

                if prev_outs:
                    ins = prev_outs
                elif self.app:
                    ins = self.app.term
                else:
                    ins = None

                outs = self.app.term if self.app else None
                errs = self.app.term if self.app else None

                if simple_command.io_redirect:
                    mode = 'w' if simple_command.io_redirect.operator == '>' else 'a'
                    outs = open(simple_command.io_redirect.filename, mode)

                if idx < n_simple_commands - 1:
                    outs = StringIO()
                elif final_outs:
                    outs = final_outs

                if _DEBUG:
                    _STDOUT.write('io %s %s\n' % (ins, outs))

                try:
                    if simple_command.cmd_word != '':
                        script_file = self.find_script_file(simple_command.cmd_word)
                        if _DEBUG:
                            _STDOUT.write('script is %s\n' % script_file)

                        with self.save_state():
                            if script_file.endswith('.py'):
                                self.retval = self.exec_py_file(script_file, simple_command, ins, outs, errs)

                            else:  # TODO: run shell script file
                                self.retval = self.exec_sh_file(script_file)

                    if self.retval != 0:
                        break  # break out of the pipe_sequence, but NOT pipeline_list

                    if isinstance(outs, StringIO):
                        outs.seek(0)  # rewind for next command in the pipe sequence

                    prev_outs = outs

                except Exception as e:
                    err_msg = '%s\n' % e.message
                    if _DEBUG:
                        _STDOUT.write(err_msg)
                    if self.app:
                        self.app.term.write_with_prefix(err_msg)
                    break  # break out of the pipe_sequence, but NOT pipeline_list

                finally:
                    if type(outs) == file:
                        outs.close()

    def exec_py_file(self, filename, simple_command, stdin=None, stdout=None, stderr=None):
        try:
            if stdin:
                sys.stdin = stdin
            if stdout:
                sys.stdout = stdout
            if stderr:
                sys.stderr = stderr
            sys.argv = [os.path.basename(filename)] + simple_command.args  # First argument is the script name
            os.environ = self.envars
            file_path = os.path.relpath(filename)
            namespace = dict(locals(), **globals())
            namespace['__name__'] = '__main__'
            namespace['__file__'] = os.path.abspath(file_path)
            namespace['_stash'] = self.app
            namespace['_stash_simple_command'] = simple_command
            execfile(file_path, namespace, namespace)
            return 0

        except SystemExit as e:
            return e.message

        except:
            err_msg = 'stash: %s\n' % sys.exc_value
            if _DEBUG:
                _STDOUT.write(err_msg)
            if self.app:
                self.app.term.write_with_prefix('%s\n' % err_msg)
            return 1

    def exec_sh_file(self, filename):
        with open(filename) as fins:
            for line in fins.readlines():
                line = line.strip()
                if line != '':
                    worker = self.run(line.strip(), add_to_history=False, reset_inp=False)
                    while worker.isAlive():  # wait for it to finish
                        pass
        return 0

    def add_history(self, s):
        if s.strip() != '' and (self.history == [] or s != self.history[0]):
            self.history.insert(0, s)
            if len(self.history) > self.HISTORY_MAX:
                self.history = self.history[0:self.HISTORY_MAX]
            self.history_listsource.items = self.history

    def save_history(self):
        try:
            with open(self.historyfile, 'w') as outs:
                outs.write('\n'.join(self.history))
        except IOError:
            pass

    def history_up(self):
        self.idx_to_history += 1
        if self.idx_to_history >= len(self.history):
            self.idx_to_history -= 1
        else:
            self.app.term.set_inp_text(self.history[self.idx_to_history])

    def history_dn(self):
        self.idx_to_history -= 1
        if self.idx_to_history <= -1:
            self.idx_to_history = -1
        else:
            self.app.term.set_inp_text(self.history[self.idx_to_history])

    def reset_idx_to_history(self):
        self.idx_to_history = -1


_GRAMMAR = r"""
-----------------------------------------------------------------------------
    Shell Grammar Simplified
-----------------------------------------------------------------------------

complete_command : pipeline_list [';']

pipeline_list         : pipeline (';' pipeline)*

pipeline         : ['!'] pipe_sequence

pipe_sequence    : simple_command ('|' simple_command)*

simple_command   : cmd_prefix [cmd_word] [cmd_suffix]
                 | cmd_word [cmd_suffix]

cmd_prefix       : assignment_word+

cmd_suffix       : word+ [io_redirect]
                 | io_redirect

io_redirect      : ('>' | '>>') filename


cmd_word         : ['\'] word
filename         : word

"""

_word_chars = r'''0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!#$%()*+,-./:=?@[]^_{}~'''

class Assignment(object):
    def __init__(self, identifier, value):
        self.identifier = identifier
        self.value = value

    def __str__(self):
        s = '%s=%s' % (self.identifier, self.value)
        return s


class IO_Redirect(object):
    def __init__(self, operator, filename):
        self.operator = operator
        self.filename = filename

    def __str__(self):
        ret = '%s %s' % (self.operator, self.filename)
        return ret


class Simple_Command(object):
    def __init__(self, assignments, modifier, cmd_word, cmd_args, io_redirect):
        self.assignments = assignments
        self.modifier = modifier
        self.cmd_word = cmd_word
        self.args = cmd_args
        self.io_redirect = io_redirect

    def __str__(self):

        s = 'assignments: %s\nmodifier: %s\ncmd_word: %s\nargs: %s\nio_redirect: %s\n' % \
            (', '.join(str(asn) for asn in self.assignments),
             self.modifier,
             self.cmd_word,
             ', '.join(self.args),
             self.io_redirect)
        return s


class Pipeline(object):
    def __init__(self, bang, pipe_sequence):
        self.bang = bang
        self.pipe_sequence = pipe_sequence

    def __str__(self):
        s = '-------- Pipeline --------\nbang: %s\n' % self.bang
        for idx, cmd in enumerate(self.pipe_sequence):
            s += '------ Simple_Command %d ------\n%s' % (idx, str(cmd))
        return s


class Complete_Command(object):
    def __init__(self, pipeline_list):
        self.pipeline_list = pipeline_list

    def __str__(self):
        s = '---------- Complete_Command ----------\n'
        for idx, pipeline in enumerate(self.pipeline_list):
            s += str(pipeline)
        return s


class ShBasicParser(object):

    class BasicWord(object):
        def __init__(self, tok, spos, epos, is_cmd):
            self.tok = tok
            self.spos = spos
            self.epos = epos
            self.is_cmd = is_cmd

    def __init__(self):
        escaped = "\\" + pp.Word(pp.printables + ' ', exact=1)
        uq_word = pp.Word(_word_chars)
        bq_word = pp.QuotedString('`', escChar='\\', unquoteResults=False)
        dq_word = pp.QuotedString('"', escChar='\\', unquoteResults=False)
        sq_word = pp.QuotedString("'", escChar='\\', unquoteResults=False)
        punctuator = pp.oneOf('; & | < >').setParseAction(self.punctuator_action)

        word = pp.Combine(pp.OneOrMore(escaped ^ escaped ^ uq_word ^ bq_word ^ dq_word ^ sq_word))\
            .setParseAction(self.word_action)
        line = pp.OneOrMore(word ^ pp.Suppress(punctuator))

        self.parser = line
        self.next_word_is_cmd = True
        self.word_stack = []

    def parse(self, line):
        self.next_word_is_cmd = True
        self.word_stack = []
        self.parser.parseString(line, parseAll=True)
        return self.word_stack

    def punctuator_action(self, s, pos, toks):
        self.next_word_is_cmd = True

    def word_action(self, s, pos, toks):
        self.word_stack.append(ShBasicParser.BasicWord(toks[0], pos, pos + len(toks[0]), self.next_word_is_cmd))
        if self.next_word_is_cmd:
            self.next_word_is_cmd = False


basic_parser = ShBasicParser()


class ShParser(object):

    def __init__(self, runtime=None):

        self.runtime = runtime
        if runtime:
            self.envars = self.runtime.envars
            self.aliases = self.runtime.aliases
            self.history = self.runtime.history
        else:
            self.envars = {}
            self.aliases = {}
            self.history = []

        self.parser, self.parser_within_dq = self.init_parser()

        # Parse State related variables
        self.state_stack = []
        self.line = ''

        self.aliases_exclude = []
        self.is_processing_args = False
        self.is_processing_assignment = False
        self.is_processing_within_dq = False
        self.bang = False
        self.pipeline_list = []
        self.pipe_sequence = []
        self.assignments = []
        self.modifier = ''
        self.cmd_word = ''
        self.cmd_args = []
        self.io_redirect = None
        self.word = ''  # unmodified word
        self.word_expanded = ''
        self.word_expanded_globable = ''  # expanded and glob ready
        self.word_expanded_globbed = None  # globbed results list

    @contextlib.contextmanager
    def save_state(self):
        self.state_stack.append([
            self.aliases_exclude,
            self.is_processing_args,
            self.is_processing_assignment,
            self.is_processing_within_dq,
            self.bang,
            self.pipeline_list,
            self.pipe_sequence,
            self.assignments,
            self.modifier,
            self.cmd_word,
            self.cmd_args,
            self.io_redirect,
            self.word,
            self.word_expanded,
            self.word_expanded_globable,
            self.word_expanded_globbed,
        ])
        try:
            yield
        finally:
            self.restore_state()

    def restore_state(self):
        (self.aliases_exclude,
         self.is_processing_args,
         self.is_processing_assignment,
         self.is_processing_within_dq,
         self.bang,
         self.pipeline_list,
         self.pipe_sequence,
         self.assignments,
         self.modifier,
         self.cmd_word,
         self.cmd_args,
         self.io_redirect,
         self.word,
         self.word_expanded,
         self.word_expanded_globable,
         self.word_expanded_globbed) = self.state_stack.pop()

    def init_parser(self):
        # Escaped characters including the whitespace
        escaped = ("\\" + pp.Word(pp.printables + ' ', exact=1)).setParseAction(self.escaped_action)

        # Unquoted Word composed of printable characters excluding & ; < > | " ' ` \
        uq_word = pp.Word(_word_chars).setParseAction(self.uq_word_action)

        # Backquoted word
        bq_word = pp.QuotedString('`', escChar='\\').setParseAction(self.bq_word_action)

        # match both single and double quoted string, recognize escapes
        dq_word = pp.QuotedString('"', escChar='\\').setParseAction(self.dq_word_action)
        sq_word = pp.QuotedString("'", escChar='\\').setParseAction(self.sq_word_action)

        # The word is a single continuous character stream
        word = pp.Combine(pp.OneOrMore(escaped ^ uq_word ^ bq_word ^ dq_word ^ sq_word))\
            .setParseAction(self.word_action)

        uq_word_in_dq = pp.Word(pp.printables.replace('`', ' ').replace('\\', ''))\
            .setParseAction(self.uq_word_in_dq_action)
        word_in_dq = pp.Combine(pp.OneOrMore(escaped ^ bq_word ^ uq_word_in_dq))

        # The use of combine is a trick to actually copy the definition of word
        cmd_word = pp.Combine(pp.Optional('\\').setParseAction(self.modifier_action) + word)\
            .setParseAction(self.cmd_word_action)
        filename = pp.Combine(word)

        identifier = pp.Word(pp.alphas + '_', pp.alphas + pp.nums + '_')

        assignment_word = (identifier + pp.Suppress('=').setParseAction(self.assignment_op_action) + word)\
            .setParseAction(self.assignment_word_action)

        io_redirect = (pp.oneOf('>> >').setParseAction(self.io_redirect_op_action) + filename)\
            .setParseAction(self.io_redirect_action)

        cmd_prefix = pp.OneOrMore(assignment_word)

        cmd_suffix = (pp.OneOrMore(word) + pp.Optional(io_redirect)) ^ io_redirect

        simple_command = ((cmd_prefix + pp.Optional(cmd_word) + pp.Optional(cmd_suffix))
                          | (cmd_word + pp.Optional(cmd_suffix)))\
            .setParseAction(self.simple_command_action)

        pipe_sequence = simple_command + pp.ZeroOrMore(pp.Suppress('|') + simple_command)

        pipeline = (pp.Optional('!').setParseAction(self.bang_action) + pipe_sequence)\
            .setParseAction(self.pipeline_action)

        pipeline_list = pipeline + pp.ZeroOrMore(pp.Suppress(';') + pipeline)

        complete_command = pipeline_list + pp.Suppress(pp.Optional(';'))

        return complete_command, word_in_dq

    def parse(self, line):

        self.line = line
        self.aliases_exclude = []

        while 1:
            self.is_processing_args = False
            self.is_processing_assignment = False
            self.is_processing_within_dq = False
            self.bang = False
            self.pipeline_list = []
            self.pipe_sequence = []
            self.assignments = []
            self.modifier = ''
            self.cmd_word = ''
            self.cmd_args = []
            self.io_redirect = None
            self.word = ''  # unmodified word
            self.word_expanded = ''
            self.word_expanded_globable = ''  # expanded and glob ready
            self.word_expanded_globbed = None  # globbed results list

            try:
                self.parser.parseString(self.line, parseAll=True)
                break
            except ShReprocess as e:
                if _DEBUG_PARSER:
                    print e.message
                continue

        return Complete_Command(self.pipeline_list)

    def expanduser(self, s):
        """ Expand part of a word """
        saved_environ = os.environ
        try:
            os.environ = self.envars
            s = os.path.expanduser(s)
            # Command substitution is done by bq_word_action
            # Pathname expansion (glob) is done in word_action
        finally:
            os.environ = saved_environ
        return s

    def expandvars(self, s):
        saved_environ = os.environ
        try:
            os.environ = self.envars
            s = os.path.expandvars(s)
        finally:
            os.environ = saved_environ
        return s

    def escape_wildcards(self, s0):
        return ''.join(('[%s]' % c if c in '[]?*' else c) for c in s0)

    def escaped_action(self, s, pos, toks):
        if _DEBUG_PARSER:
            print 'escaped_action'
        c = toks[1]
        if c == 't':
            self.word_expanded += '\t'
            self.word_expanded_globable += '\t'
        elif c == 'r':
            self.word_expanded += '\r'
            self.word_expanded_globable += '\r'
        elif c == 'n':
            self.word_expanded += '\n'
            self.word_expanded_globable += '\n'
        else:
            self.word_expanded += c
            if c in '[]?*':
                self.word_expanded_globable += '[%s]' % c
            else:
                self.word_expanded_globable += c

    def uq_word_action(self, s, pos, toks):
        if _DEBUG_PARSER:
            print 'uq_word_action'
        s = self.expandvars(self.expanduser(toks[0]))
        self.word_expanded += s
        self.word_expanded_globable += s

    def uq_word_in_dq_action(self, s, pos, toks):
        # Only expand variable, all wildcards should be escaped
        if _DEBUG_PARSER:
            print 'uq_word_in_dq_action'
        s = self.expandvars(toks[0])
        self.word_expanded += s
        self.word_expanded_globable += self.escape_wildcards(s)

    def bq_word_action(self, s, pos, toks):
        if _DEBUG_PARSER:
            print 'bq_word_action'

        bqs = toks[0]
        if self.runtime:
            with self.save_state():
                outs = StringIO()
                worker = self.runtime.callback_run(bqs, final_outs=outs)
                while worker.isAlive():
                    pass
                ret = ' '.join(outs.getvalue().splitlines())
        else:
            ret = '_from_backquotes_'  # dummy, debug on pc only

        if self.is_processing_assignment or self.is_processing_within_dq:
            self.word_expanded += ret
            self.word_expanded_globable += ret
        else:
            self.line = s[0:pos] + ret + s[pos + len(toks[0]) + 2:]  # +2 for the quotes
            raise ShReprocess('Backquotes found. Reprocessing %s' % self.line)

    def dq_word_action(self, s, pos, toks):
        if _DEBUG_PARSER:
            print 'dq_word_action'
        self.is_processing_within_dq = True
        self.parser_within_dq.parseString(toks[0], parseAll=True)
        self.is_processing_within_dq = False

    def sq_word_action(self, s, pos, toks):
        if _DEBUG_PARSER:
            print 'sq_word_action'
        self.word_expanded += toks[0]
        self.word_expanded_globable += self.escape_wildcards(toks[0])

    def word_action(self, s, pos, toks):
        if _DEBUG_PARSER:
            print 'word_action'
        self.word = toks[0]
        self.word_expanded_globbed = glob.glob(self.word_expanded_globable)

        if self.is_processing_args:
            self.cmd_args += self.word_expanded_globbed if self.word_expanded_globbed else [self.word_expanded]
            self.word_expanded = ''

        self.word_expanded_globable = ''

    def modifier_action(self, s, pos, toks):
        if _DEBUG_PARSER:
            print 'modifier_action'
        if len(toks) > 0:
            self.modifier = toks[0]

    def cmd_word_action(self, s, pos, toks):
        if _DEBUG_PARSER:
            print 'cmd_word'

        if self.bang:  # history search, no expansion needed
            for h in self.history:
                if h.startswith(toks[0]):  # toks[0] instead of self.word in case cmd_word has leading modifier
                    self.line = h + s[pos + len(toks[0]):]
                    raise ShReprocess('History matched. Reprocessing %s' % self.line)
            raise Exception('%s: Event not found' % toks[0])

        else:
            if self.word_expanded_globbed:
                self.cmd_word = self.word_expanded_globbed[0]
                if len(self.word_expanded_globbed) > 1:
                    self.cmd_args = self.word_expanded_globbed[1:]
            else:
                self.cmd_word = self.word_expanded

            self.is_processing_args = True
            self.word_expanded = ''

    def assignment_op_action(self, s, pos, toks):
        self.is_processing_assignment = True

    def assignment_word_action(self, s, pos, toks):
        if _DEBUG_PARSER:
            print 'assignment_word'
        if self.word_expanded_globbed:
            self.assignments.append(Assignment(toks[0], ' '.join(self.word_expanded_globbed)))
        else:
            self.assignments.append(Assignment(toks[0], self.word_expanded))
        self.is_processing_assignment = False
        self.word_expanded = ''

    def io_redirect_op_action(self, s, pos, toks):
        if _DEBUG_PARSER:
            print 'io_redirect_op_action'
        self.is_processing_args = False

    def io_redirect_action(self, s, pos, toks):
        if _DEBUG_PARSER:
            print 'io_redirect'
        if self.io_redirect is not None:
            raise Exception('Multiple io redirection not allowed')
        else:
            if len(self.word_expanded_globbed) == 1:
                self.io_redirect = IO_Redirect(toks[0], self.word_expanded_globbed[0])
            elif len(self.word_expanded_globbed) > 1:
                raise Exception('Ambiguous redirect: %s' % self.word_expanded)
            else:
                self.io_redirect = IO_Redirect(toks[0], self.word_expanded)
        self.word_expanded = ''

    def simple_command_action(self, s, pos, toks):
        if _DEBUG_PARSER:
            print 'simple_command'
        self.pipe_sequence.append(Simple_Command(self.assignments,
                                                 self.modifier,
                                                 self.cmd_word,
                                                 self.cmd_args,
                                                 self.io_redirect))
        # When a simple command ends, the processing of arguments should end as well
        # and reset the args list
        self.is_processing_args = False
        self.modifier = ''
        self.cmd_args = []
        self.assignments = []

    def bang_action(self, s, pos, toks):
        if _DEBUG_PARSER:
            print 'bang'

        if toks:
            self.bang = True

        else:  # non-history, expand aliases first
            self.bang = False
            line = ''
            words = basic_parser.parse(self.line)
            last_pos = 0
            for w in words:
                line += self.line[last_pos: w.spos]
                if w.is_cmd and not w.tok.startswith('\\') \
                        and w.tok in self.aliases.keys() and w.tok not in self.aliases_exclude:
                    line += self.aliases[w.tok]
                    self.aliases_exclude.append(w.tok)
                else:
                    line += w.tok
                last_pos = w.epos

            if line != self.line:  # alias found and expanded
                self.line = line
                raise ShReprocess("Alias found. Reprocessing %s" % self.line)

    def pipeline_action(self, s, pos, toks):
        if _DEBUG_PARSER:
            print 'pipeline'
        self.pipeline_list.append(Pipeline(self.bang, self.pipe_sequence))
        # When pipeline ends, reset the pipe sequence
        self.pipe_sequence = []


class ShCompleter(object):

    def __init__(self, app=None):
        self.app = app

    def complete(self, line):
        is_cmd_word = False
        has_trailing_white = False
        word_to_complete = ''

        if line.strip() == '':  # all commands + py files in current directory + all alias
            all_names = self.app.runtime.get_all_script_names()
            all_names.extend(self.app.runtime.aliases.keys())

        else:
            try:
                words = basic_parser.parse(line)
                if len(line) > words[-1].epos:
                    has_trailing_white = True
                word_to_complete = words[-1].tok
                word_to_complete_normal_whites = word_to_complete.replace('\\ ', ' ')
                is_cmd_word = words[-1].is_cmd
            except pp.ParseException as e:
                self.app.term.write_with_prefix('parsing error: at char %d: %s\n' % (e.loc, e.pstr))

            if has_trailing_white:  # files in current directory
                all_names = [f for f in os.listdir('.')]

            elif is_cmd_word:  # commands match + alias match + path match
                script_names = [script_name for script_name in self.app.runtime.get_all_script_names()
                                if script_name.startswith(word_to_complete_normal_whites)]
                alias_names = [aln for aln in self.app.runtime.aliases.keys()
                               if aln.startswith(word_to_complete_normal_whites)]
                path_names = []
                for p in self.path_match(word_to_complete_normal_whites):
                    if not os.path.isdir(p) and (p.endswith('.py') or p.endswith('.sh')):
                        path_names.append(p)

                all_names = script_names + alias_names + path_names
            else:  # path match
                all_names = self.path_match(word_to_complete_normal_whites)

            # If the partial word starts with a dollar sign, try envar match
            if word_to_complete_normal_whites.startswith('$'):
                all_names.extend('$' + varname for varname in self.app.runtime.envars.keys()
                                 if varname.startswith(word_to_complete_normal_whites[1:]))

        all_names = sorted(set(all_names))

        if len(all_names) > 30:
            if self.app:
                self.app.term.write('%s\nMore than %d possibilities\n'
                                    % (self.app.term.inp.text, 30))
            if _DEBUG_COMPLETER:
                print self.format_all_names(all_names)

        else:
            # Complete up to the longest common prefix of all possibilities
            prefix = os.path.commonprefix(all_names)

            if prefix != '':
                if line.strip() == '' or has_trailing_white:
                    newline = line + prefix

                else:
                    search_string = word_to_complete
                    replace_string = os.path.join(os.path.dirname(word_to_complete), prefix.replace(' ', '\\ '))
                    # reverse to make sure only the rightmost match is replaced
                    newline = line[::-1].replace(search_string[::-1], replace_string[::-1], 1)[::-1]
            else:
                newline = line

            if len(all_names) == 1:
                newline += ' '

            if newline != line:
                # No need to show available possibilities if some completion can be done
                if self.app:
                    self.app.term.set_inp_text(newline)  # Complete the line
                else:
                    if _DEBUG_COMPLETER:
                        print repr(line)
                        print repr(newline)

            elif len(all_names) > 0:  # no completion available, show all possibilities if exist
                if self.app:
                    self.app.term.write('%s\n%s\n'
                                        % (self.app.term.inp.text, self.format_all_names(all_names)))
                if _DEBUG_COMPLETER:
                    print self.format_all_names(all_names)

    def path_match(self, word_to_complete_normal_whites):
        if os.path.isdir(word_to_complete_normal_whites) and word_to_complete_normal_whites.endswith('/'):
            filenames = [fname for fname in os.listdir(word_to_complete_normal_whites)]
        else:
            d = os.path.expanduser(os.path.dirname(word_to_complete_normal_whites)) or '.'
            f = os.path.basename(word_to_complete_normal_whites)
            try:
                filenames = [fname for fname in os.listdir(d) if fname.startswith(f)]
            except:
                filenames = []
        return filenames

    def format_all_names(self, all_names):
        return '  '.join(all_names) + '\n'


class ShTerm(ui.View):
    """
    The View as the terminal of the application
    """

    def __init__(self, app):

        self.app = app

        self.flush_recheck_delay = 0.1  # seconds
        self._flush_thread = None
        self._timer_to_start_flush_thread = None
        self._n_refresh = 5
  
        self.BUFFER_MAX = app.config.getint('display', 'BUFFER_MAX')
        self.TEXT_FONT = eval(app.config.get('display', 'TEXT_FONT'))
        self.BUTTON_FONT = eval(app.config.get('display', 'BUTTON_FONT'))

        self.inp_buf = []
        self.out_buf = ''
        self.input_did_return = False  # For command with raw_input
        self.cleanup = app.will_close

        # TODO: Setup the prompt based on rcfile
        self.prompt = '$ '

        # Start constructing the view's layout
        self.name = 'stash'
        self.flex = 'WH'
        self.background_color = 0.0
  
        self.txts = ui.View(name='txts', flex='WH')  # Wrapper view of output and input areas
        self.add_subview(self.txts)
        self.txts.background_color = 0.7
  
        self.vks = ui.View(name='vks', flex='WT')
        self.txts.add_subview(self.vks)
        self.vks.background_color = 0.7
  
        k_hspacing = 2
  
        self.k_tab = ui.Button(name='k_tab', title=' Tab ', flex='TB')
        self.vks.add_subview(self.k_tab)
        self.k_tab.action = app.vk_tapped
        self.k_tab.font = self.BUTTON_FONT
        self.k_tab.border_width = 1
        self.k_tab.border_color = 0.9
        self.k_tab.corner_radius = 5
        self.k_tab.tint_color = 'black'
        self.k_tab.background_color = 'white'
        self.k_tab.size_to_fit()
   
        self.k_hist = ui.Button(name='k_hist', title=' Hist ', flex='RTB')
        self.vks.add_subview(self.k_hist)
        self.k_hist.action = app.vk_tapped
        self.k_hist.font = self.BUTTON_FONT
        self.k_hist.border_width = 1
        self.k_hist.border_color = 0.9
        self.k_hist.corner_radius = 5
        self.k_hist.tint_color = 'black'
        self.k_hist.background_color = 'white'
        self.k_hist.size_to_fit()
        self.k_hist.x = self.k_tab.width + k_hspacing

        self.k_hup = ui.Button(name='k_hup', title=' Up ', flex='RTB')
        self.vks.add_subview(self.k_hup)
        self.k_hup.action = app.vk_tapped
        self.k_hup.font = self.BUTTON_FONT
        self.k_hup.border_width = 1
        self.k_hup.border_color = 0.9
        self.k_hup.corner_radius = 5
        self.k_hup.tint_color = 'black'
        self.k_hup.background_color = 'white'
        self.k_hup.size_to_fit()
        self.k_hup.x = self.k_hist.x + self.k_hist.width + k_hspacing

        self.k_hdn = ui.Button(name='k_hdn', title=' Dn ', flex='RTB')
        self.vks.add_subview(self.k_hdn)
        self.k_hdn.action = app.vk_tapped
        self.k_hdn.font = self.BUTTON_FONT
        self.k_hdn.border_width = 1
        self.k_hdn.border_color = 0.9
        self.k_hdn.corner_radius = 5
        self.k_hdn.tint_color = 'black'
        self.k_hdn.background_color = 'white'
        self.k_hdn.size_to_fit()
        self.k_hdn.x = self.k_hup.x + self.k_hup.width + k_hspacing

        self.k_CD = ui.Button(name='k_CD', title=' C-D ', flex='RTB')
        self.vks.add_subview(self.k_CD)
        self.k_CD.action = app.vk_tapped
        self.k_CD.font = self.BUTTON_FONT
        self.k_CD.border_width = 1
        self.k_CD.border_color = 0.9
        self.k_CD.corner_radius = 5
        self.k_CD.tint_color = 'black'
        self.k_CD.background_color = 'white'
        self.k_CD.size_to_fit()
        self.k_CD.x = self.k_hdn.x + self.k_hdn.width + k_hspacing

        self.k_CC = ui.Button(name='k_CC', title=' C-C ', flex='RTB')
        self.vks.add_subview(self.k_CC)
        self.k_CC.action = app.vk_tapped
        self.k_CC.font = self.BUTTON_FONT
        self.k_CC.border_width = 1
        self.k_CC.border_color = 0.9
        self.k_CC.corner_radius = 5
        self.k_CC.tint_color = 'black'
        self.k_CC.background_color = 'white'
        self.k_CC.size_to_fit()
        self.k_CC.x = self.k_CD.x + self.k_CD.width + k_hspacing
  
        self.vks.height = self.k_hist.height
        self.vks.y = self.vks.superview.height - (self.vks.height + 4)
  
        self.inp = ui.TextField(name='inp', flex='WT')
        self.txts.add_subview(self.inp)
        self.inp.font = self.TEXT_FONT
        self.inp.height = self.TEXT_FONT[1] + 2
        self.inp.y = self.inp.superview.height - (self.inp.height + 4) - (self.vks.height + 4)
        self.inp.background_color = eval(app.config.get('display', 'INPUT_BACKGROUND_COLOR'))
        self.inp.text_color = eval(app.config.get('display', 'INPUT_TEXT_COLOR'))
        self.inp.tint_color = eval(app.config.get('display', 'INPUT_TINT_COLOR'))
        self.inp.text = self.prompt
        self.inp.bordered = False
        self.inp.clear_button_mode = 'always'
        self.inp.autocapitalization_type = ui.AUTOCAPITALIZE_NONE
        self.inp.autocorrection_type = False
        self.inp.delegate = app
  
        self.out = ui.TextView(name='out', flex='WH')
        self.txts.add_subview(self.out)
        self.out.height = self.out.superview.height - (self.inp.height + 4) - (self.vks.height + 4)
        self.out.auto_content_inset = False
        self.out.content_inset = (0, 0, -8, 0)
        self.out.background_color = eval(app.config.get('display', 'OUTPUT_BACKGROUND_COLOR'))
        self.out.indicator_style = app.config.get('display', 'OUTPUT_INDICATOR_STYLE')
        self.out.font = self.TEXT_FONT
        self.out.text_color = eval(app.config.get('display', 'OUTPUT_TEXT_COLOR'))
        self.out.tint_color = eval(app.config.get('display', 'OUTPUT_TINT_COLOR'))
        self.out.text = ''
        self.out.editable = False
        self.out.delegate = app

    def will_close(self):
        self.cleanup()

    def keyboard_frame_did_change(self, frame):
        if frame[3] > 0:
            self.txts.height = self.height - frame[3]
            self.flush()
        else:
            self.txts.height = self.height

    def read_inp_line(self):
        return self.inp.text[len(self.prompt):]
  
    def reset_inp(self):
        self.set_inp_text('')
  
    def set_inp_text(self, s, with_prompt=True):
        if with_prompt:
            self.prompt = self.app.get_prompt()
            self.inp.text = '%s%s' % (self.prompt, s)
        else:
            self.inp.text = s
 
    def add_out_buf(self, s):
        """Control the buffer size"""
        if s != '':
            self.out_buf += s
 
    # File-like objects for IO redirect of external scripts
    # read functions are only called by external script as raw_input
    def read(self, size=-1):
        return self.readline()

    def readline(self, size=-1):
        while not self.input_did_return:
            pass
        self.input_did_return = False
        # Read from input buffer instead of term directly.
        # This allows the term to response more quickly to user interactions.
        if self.inp_buf:
            line = self.inp_buf.pop()
            line = line[:int(size)] if size >= 0 else line
        else:
            line = ''
        return line

    def readlines(self, size=-1):
        while not self.input_did_return:
            pass
        self.input_did_return = False
        lines = [line + '\n' for line in self.inp_buf]
        self.inp_buf = []
        return lines

    def clear(self):
        self.out_buf = ''
        self.flush()

    def write(self, s):
        if _DEBUG:
            _STDOUT.write('Write Called: [%s]\n' % repr(s))
        self.add_out_buf(s)
        self.flush()

    def write_with_prefix(self, s):
        self.write('stash: ' + s)

    def writelines(self, lines):
        if _DEBUG:
            _STDOUT.write('Writeline Called: [%s]\n' % repr(lines))
        self.write(''.join(lines))

    def flush(self):
        # Throttle the flush by allowing only one running _flush thread
        if self._flush_thread is None or not self._flush_thread.isAlive():
            # No running flush thread, create one
            self._flush_thread = self._flush()  # in background

        else:  # A flush thread is running, make sure we check back after a delay
            if self._timer_to_start_flush_thread is None \
                    or not self._timer_to_start_flush_thread.isAlive() \
                    or threading.currentThread() == self._timer_to_start_flush_thread:
                # A timer is set if:
                #     1. No timer is set
                #     2. Timer is not alive (expired)
                #     3. Timer is alive but we are now in the thread of the time, i.e.
                #        the timer will stop right after this function ends
                self._timer_to_start_flush_thread = sh_delay(self.flush, self.flush_recheck_delay)

    # Always run in background, otherwise it may crash the app when external script
    # print many lines.
    @sh_background('_flush_thread')
    def _flush(self):
        lines = self.out_buf.splitlines(True)
        nlines = len(lines)
        if nlines > self.BUFFER_MAX:
            lines = lines[nlines - self.BUFFER_MAX:]
            self.out_buf = ''.join(lines)
        self.out.text = self.out_buf
        self._scroll_to_end()

    def _scroll_to_end(self):
        # Have to scroll multiple times to get the correct scroll to the end effect.
        # This is because content_size reported by the ui system is not reliable.
        # It is either a bug or due to the asynchronous nature of the ui system.
        for i in range(self._n_refresh):
            self.out.content_offset = (0, self.out.content_size[1] - self.out.height)
            if i < self._n_refresh - 1:
                time.sleep(0.01)
              
    def history_present(self, listsource):
        table = ui.TableView()
        listsource.font = self.BUTTON_FONT
        table.data_source = listsource
        table.delegate = listsource
        table.width = 300
        table.height = 300
        table.row_height = self.BUTTON_FONT[1] + 4
        table.present('popover')
        table.wait_modal()
          

_DEFAULT_CONFIG = """[system]
cfgfile=.stash_config
rcfile=.stashrc
historyfile=.stash_history

[display]
TEXT_FONT=('DejaVuSansMono', 12)
BUTTON_FONT=('DejaVuSansMono', 14)
OUTPUT_BACKGROUND_COLOR=(0.0, 0.0, 0.0)
OUTPUT_TEXT_COLOR=(1.0, 1.0, 1.0)
OUTPUT_TINT_COLOR=(0.0, 0.0, 1.0)
OUTPUT_INDICATOR_STYLE=white
INPUT_BACKGROUND_COLOR=(0.3, 0.3, 0.3)
INPUT_TEXT_COLOR=(1.0, 1.0, 1.0)
INPUT_TINT_COLOR=(0.0, 0.0, 1.0)
HISTORY_MAX=30
BUFFER_MAX=100
"""


class StaSh(object):
    """
    The application class, also acts as the controller.
    """
      
    def __init__(self):

        self.thread = threading.currentThread()

        self.config = self.load_config()
        self.term = ShTerm(self)
        self.runtime = ShRuntime(self)
        self.completer = ShCompleter(self)

        #TODO: Better way to detect iPad
        self.ON_IPAD = ui.get_screen_size()[1] >= 708

        # Navigate to the startup folder
        os.chdir(self.runtime.envars['HOME2'])
        # parse rc file
        self.runtime.load_rcfile()
        self.term.write('StaSh v%s\n' % __version__)
        self.term.reset_inp()  # prompt

    @staticmethod
    def load_config():
        config = ConfigParser()
        config.optionxform = str # make it preserve case
        # defaults
        config.readfp(StringIO(_DEFAULT_CONFIG))
        # update from config file
        config.read(os.path.expanduser(config.get('system', 'cfgfile')))
        return config

    def get_prompt(self):
        prompt = self.runtime.envars['PROMPT']
        if prompt.find('\\w') or prompt.find('\\W'):
            curdir = os.getcwd().replace(self.runtime.envars['HOME'], '~')
            prompt = prompt.replace('\\w', curdir)
            prompt = prompt.replace('\\W',
                                    curdir if os.path.dirname(curdir) == '~' else os.path.basename(curdir))
        return prompt

    def textfield_did_begin_editing(self, textfield):
        pass
       
    def textfield_should_return(self, textfield):
        if not self.runtime.worker_stack:
            # No thread is running. We are to process the command entered
            # from the GUI.
            line = self.term.read_inp_line()
            if line.strip() != '':
                self.term.write('\n%s\n' % self.term.inp.text)
                self.term.set_inp_text('', with_prompt=False)
                self.term.inp_buf = []  # clear input buffer for new command
                self.runtime.reset_idx_to_history()
                self.runtime.run(line)
            else:
                self.term.write('\n')
                self.term.reset_inp()

        else:
            # we have a running threading, all inputs are considered as
            # directed to the thread, NOT the main GUI program
            self.term.inp_buf.append(self.term.inp.text)
            self.term.write('%s\n' % self.term.inp.text)
            self.term.set_inp_text('', with_prompt=False)
            self.term.input_did_return = True

        return True
  
    def textfield_did_end_editing(self, textfield):
        pass
  
    def textfield_did_change(self, textfield):
        if not self.runtime.worker_stack:
            if len(textfield.text) < len(self.term.prompt):  # Do not erase the prompt
                self.term.reset_inp()
  
    def vk_tapped(self, vk):
        if vk == self.term.k_tab:  # Tab completion
            if not self.runtime.worker_stack:
                self.completer.complete(self.term.read_inp_line())

        elif vk == self.term.k_hist:
            if not self.runtime.worker_stack:
                self.term.history_present(self.runtime.history_listsource)

        elif vk == self.term.k_hup:
            if not self.runtime.worker_stack:
                self.runtime.history_up()

        elif vk == self.term.k_hdn:
            if not self.runtime.worker_stack:
                self.runtime.history_dn()

        elif vk == self.term.k_CD:
            if self.runtime.worker_stack:
                self.term.input_did_return = True

        elif vk == self.term.k_CC:
            if not self.runtime.worker_stack:
                self.term.write_with_prefix('no thread to terminate\n')

            else:  # ctrl-c terminates the entire stack of threads
                for worker in self.runtime.worker_stack[::-1]:
                    worker._Thread__stop()
                    time.sleep(0.5)
                    if worker.isAlive():
                        self.term.write_with_prefix('failed to terminate thread: %s\n' % worker)
                        self.term.write_with_prefix('%d threads are still running ...' % len(self.runtime.worker_stack))
                        self.term.write_with_prefix('Try Ctrl-C again or restart the shell or even Pythonista\n')
                        break
                    else:
                        self.runtime.worker_stack.pop()
                        self.runtime.restore_state()  # Manually stopped thread does not restore state
                        self.term.write_with_prefix('successfully terminated thread %s\n' % worker)
                self.term.reset_inp()

    def history_popover_tapped(self, sender):
        if sender.selected_row >= 0: 
            self.term.set_inp_text(sender.items[sender.selected_row])

    def will_close(self):
        self.runtime.save_history()
 
    def run(self):
        self.term.present('panel')
        self.term.inp.begin_editing()
   
   
if __name__ == '__main__':
    if _IN_PYTHONISTA:
        stash = StaSh()
        stash.run()

