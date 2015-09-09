# coding: utf-8
"""
StaSh - Pythonista Shell

https://github.com/ywangd/stash
"""

__version__ = '0.5.0'

import os
import sys
from ConfigParser import ConfigParser
from StringIO import StringIO
import functools
import glob
import imp as pyimp  # rename to avoid name conflict with objc_util
import string
import threading
import logging
import logging.handlers

import pyparsing as pp

# Detecting environments
IN_PYTHONISTA = True
try:
    import ui
    import console
except ImportError:
    import system.dummyui as ui
    import system.dummyconsole as console
    IN_PYTHONISTA = False

PYTHONISTA_VERSION = '1.6'
try:
    from objc_util import *
except ImportError:
    from system.dummyobjc_util import *
    PYTHONISTA_VERSION = '1.5'

from platform import platform
if platform().find('iPad') != -1:
    ON_IPAD = True
else:
    ON_IPAD = False


# noinspection PyPep8Naming
from system.shcommon import Graphics as graphics, Control as ctrl, Escape as esc
from system.shstreams import ShMiniBuffer, ShStream
from system.shscreens import ShSequentialScreen, ShSequentialRenderer
from system.shui import ShUI
from system.shio import ShIO

# Save the true IOs
_SYS_STDOUT = sys.stdout
_SYS_STDERR = sys.stderr
_SYS_STDIN = sys.stdin
_SYS_PATH = sys.path
_OS_ENVIRON = os.environ

# Setup logging
LOGGER = logging.getLogger('StaSh')

# Debugging constants
_DEBUG_STREAM = 200
_DEBUG_RENDERER = 201
_DEBUG_MAIN_SCREEN = 202
_DEBUG_MINI_BUFFER = 203
_DEBUG_IO = 204
_DEBUG_UI = 300
_DEBUG_TERMINAL = 301
_DEBUG_TV_DELEGATE = 302
_DEBUG_RUNTIME = 400
_DEBUG_PARSER = 401
_DEBUG_EXPANDER = 402
_DEBUG_COMPLETER = 403

_STASH_ROOT = os.path.realpath(os.path.abspath(os.path.dirname(__file__)))
# Resource files
_STASH_CONFIG_FILE = '.stash_config'
_STASH_RCFILE = '.stashrc'
_STASH_HISTORY_FILE = '.stash_history'

# Default configuration (can be overridden by external configuration file)
_DEFAULT_CONFIG = """[system]
py_traceback=0
py_pdb=0
input_encoding_utf8=1
ipython_style_history_search=1

[display]
TEXT_FONT_SIZE={text_size}
BUTTON_FONT_SIZE=14
BACKGROUND_COLOR=(0.0, 0.0, 0.0)
TEXT_COLOR=(1.0, 1.0, 1.0)
TINT_COLOR=(0.0, 0.0, 1.0)
INDICATOR_STYLE=white
HISTORY_MAX=50
BUFFER_MAX=150
AUTO_COMPLETION_MAX=50
VK_SYMBOLS=~/.-*|>$'=!&_"\?`
""".format(text_size=14 if ON_IPAD else 12)

# Default .stashrc file
_DEFAULT_RC = r"""BIN_PATH=~/Documents/bin:$BIN_PATH
SELFUPDATE_BRANCH=master
PYTHONPATH=$STASH_ROOT/lib
alias env='printenv'
alias logout='echo "Use the close button in the upper right corner to exit StaSh."'
alias help='man'
alias la='ls -a'
alias ll='ls -la'
alias copy='pbcopy'
alias paste='pbpaste'
"""


class ShFileNotFound(Exception):
    pass

class ShIsDirectory(Exception):
    pass

class ShSingleExpansionRequired(Exception):
    pass

class ShEventNotFound(Exception):
    pass

class ShBadSubstitution(Exception):
    pass

class ShSyntaxError(Exception):
    pass

class ShInternalError(Exception):
    pass

class ShKeyboardInterrupt(Exception):
    pass

def sh_background(name=None):
    def wrap(func):
        @functools.wraps(func)
        def wrapped_func(*args, **kwargs):
            t = threading.Thread(name=name, target=func, args=args, kwargs=kwargs)
            t.start()
            return t
        return wrapped_func
    return wrap


_GRAMMAR = r"""
-----------------------------------------------------------------------------
    Shell Grammar Simplified
-----------------------------------------------------------------------------

complete_command : pipe_sequence (punctuator pipe_sequence)* [punctuator]

punctuator       : ';' | '&'

pipe_sequence    : simple_command ('|' simple_command)*

simple_command   : cmd_prefix [cmd_word] [cmd_suffix]
                 | cmd_word [cmd_suffix]

cmd_prefix       : assignment_word+

cmd_suffix       : word+ [io_redirect]
                 | io_redirect

io_redirect      : ('>' | '>>') filename

modifier         : '!' | '\'

cmd_word         : [modifier] word
filename         : word

"""

_word_chars = string.digits + string.ascii_letters + r'''!#$%()*+,-./:=?@[]^_{}~'''

class ShAssignment(object):
    def __init__(self, identifier, value):
        self.identifier = identifier
        self.value = value

    def __repr__(self):
        s = '%s=%s' % (self.identifier, self.value)
        return s

class ShIORedirect(object):
    def __init__(self, operator, filename):
        self.operator = operator
        self.filename = filename

    def __repr__(self):
        ret = '%s %s' % (self.operator, self.filename)
        return ret

class ShSimpleCommand(object):
    def __init__(self):
        self.assignments = []
        self.cmd_word = ''
        self.args = []
        self.io_redirect = None

    def __repr__(self):

        s = 'assignments: %s\ncmd_word: %s\nargs: %s\nio_redirect: %s\n' % \
            (', '.join(str(asn) for asn in self.assignments),
             self.cmd_word,
             ', '.join(self.args),
             self.io_redirect)
        return s

class ShPipeSequence(object):
    def __init__(self):
        self.in_background = False
        self.lst = []

    def __repr__(self):
        s = '-------- ShPipeSequence --------\n'
        s += 'in_background: %s\n' % self.in_background
        for idx, cmd in enumerate(self.lst):
            s += '------ ShSimpleCommand %d ------\n%s' % (idx, repr(cmd))
        return s

class ShCompleteCommand(object):
    def __init__(self):
        self.lst = []

    def __repr__(self):
        s = '\n---------- ShCompleteCommand ----------\n'
        for idx, pipe_sequence in enumerate(self.lst):
            s += repr(pipe_sequence)
        return s


class ShToken(object):

    _PUNCTUATOR = '_PUNCTUATOR'
    _PIPE_OP = '_PIPE_OP'
    _IO_REDIRECT_OP = '_IO_REDIRECT_OP'
    _ESCAPED = '_ESCAPED'
    _ESCAPED_OCT = '_ESCAPED_OCT'
    _ESCAPED_HEX = '_ESCAPED_HEX'
    _UQ_WORD = '_UQ_WORD'
    _BQ_WORD = '_BQ_WORD'
    _DQ_WORD = '_DQ_WORD'
    _SQ_WORD = '_SQ_WORD'
    _WORD = '_WORD'
    _FILE = '_FILE'
    _ASSIGN_WORD = '_ASSIGN_WORD'
    _CMD = '_CMD'

    def __init__(self, tok='', spos=-1, ttype=None, parts=None):
        self.tok = tok
        self.spos = spos
        self.epos = spos + len(tok)
        self.ttype = ttype if ttype else ShToken._WORD
        self.parts = parts

    def __repr__(self):
        ret = '{%s %d-%d %s %s}' % (self.tok, self.spos, self.epos, self.ttype, self.parts)
        return ret


# noinspection PyProtectedMember
class ShParser(object):

    """
    Parse the command line input to provide basic semantic analysis.
    The results will be further expanded by `ShExpander`.
    """
    _NEXT_WORD_CMD = '_NEXT_WORD_CMD'
    _NEXT_WORD_VAL = '_NEXT_WORD_VAL'  # rhs of assignment
    _NEXT_WORD_FILE = '_NEXT_WORD_FILE'

    def __init__(self, debug=False):

        self.debug = debug
        self.logger = logging.getLogger('StaSh.Parser')

        escaped = pp.Combine("\\" + pp.Word(pp.printables + ' ', exact=1)).setParseAction(self.escaped_action)
        escaped_oct = pp.Combine(
            "\\" + pp.Word('01234567', max=3)
        ).setParseAction(self.escaped_oct_action)
        escaped_hex = pp.Combine(
            "\\x" + pp.Word('0123456789abcdefABCDEF', exact=2)
        ).setParseAction(self.escaped_hex_action)
        uq_word = pp.Word(_word_chars).setParseAction(self.uq_word_action)
        bq_word = pp.QuotedString('`', escChar='\\', unquoteResults=False).setParseAction(self.bq_word_action)
        dq_word = pp.QuotedString('"', escChar='\\', unquoteResults=False).setParseAction(self.dq_word_action)
        sq_word = pp.QuotedString("'", escChar='\\', unquoteResults=False).setParseAction(self.sq_word_action)
        # The ^ operator means longest match (as opposed to | which means first match)
        word = pp.Combine(pp.OneOrMore(escaped ^ escaped_oct ^ escaped_hex
                                       ^ uq_word ^ bq_word ^ dq_word ^ sq_word))\
            .setParseAction(self.word_action)

        identifier = pp.Word(pp.alphas + '_', pp.alphas + pp.nums + '_').setParseAction(self.identifier_action)
        assign_op = pp.Literal('=').setParseAction(self.assign_op_action)
        assignment_word = pp.Combine(identifier + assign_op + word).setParseAction(self.assignment_word_action)

        punctuator = pp.oneOf('; &').setParseAction(self.punctuator_action)
        pipe_op = pp.Literal('|').setParseAction(self.pipe_op_action)
        io_redirect_op = pp.oneOf('>> >').setParseAction(self.io_redirect_op_action)
        io_redirect = (io_redirect_op + word)('io_redirect')

        # The optional ' ' is a workaround to a possible bug in pyparsing.
        # The position of cmd_word after cmd_prefix is always reported 1 character ahead
        # of the correct value.
        cmd_prefix = (pp.OneOrMore(assignment_word) + pp.Optional(' '))('cmd_prefix')
        cmd_suffix = (pp.OneOrMore(word)('args') + pp.Optional(io_redirect)) ^ io_redirect

        modifier = pp.oneOf('! \\')
        cmd_word = (pp.Combine(pp.Optional(modifier) + word) ^ word)('cmd_word').setParseAction(self.cmd_word_action)

        simple_command = \
            (cmd_prefix + pp.Optional(cmd_word) + pp.Optional(cmd_suffix)) \
            | (cmd_word + pp.Optional(cmd_suffix))
        simple_command = pp.Group(simple_command)

        pipe_sequence = simple_command + pp.ZeroOrMore(pipe_op + simple_command)
        pipe_sequence = pp.Group(pipe_sequence)

        complete_command = pp.Optional(pipe_sequence
                                       + pp.ZeroOrMore(punctuator + pipe_sequence)
                                       + pp.Optional(punctuator))

        # --- special parser for inside double quotes
        uq_word_in_dq = pp.Word(pp.printables.replace('`', ' ').replace('\\', ''))\
            .setParseAction(self.uq_word_action)
        word_in_dq = pp.Combine(pp.OneOrMore(escaped ^ escaped_oct ^ escaped_hex ^ bq_word ^ uq_word_in_dq))
        # ---

        self.parser = complete_command.parseWithTabs().ignore(pp.pythonStyleComment)
        self.parser_within_dq = word_in_dq.leaveWhitespace()
        self.next_word_type = ShParser._NEXT_WORD_CMD
        self.tokens = []
        self.parts = []

    def parse(self, line):
        if self.debug:
            self.logger.debug('line: %s' % repr(line))
        self.next_word_type = ShParser._NEXT_WORD_CMD
        self.tokens = []
        self.parts = []
        parsed = self.parser.parseString(line, parseAll=True)
        return self.tokens, parsed

    def parse_within_dq(self, s):
        """ Take the input string as if it is inside a pair of double quotes
        """
        self.parts = []
        parsed = self.parser_within_dq.parseString(s, parseAll=True)
        return self.parts, parsed

    def identifier_action(self, s, pos, toks):
        """ This function is only needed for debug """
        if self.debug:
            self.logger.debug('identifier: %d, %s' % (pos, toks[0]))

    def assign_op_action(self, s, pos, toks):
        if self.debug:
            self.logger.debug(toks[0])
        self.next_word_type = ShParser._NEXT_WORD_VAL

    def assignment_word_action(self, s, pos, toks):
        if self.debug:
            self.logger.debug(toks[0])
        self.add_token(toks[0], pos, ShToken._ASSIGN_WORD, self.parts)
        self.parts = []
        self.next_word_type = ShParser._NEXT_WORD_CMD

    def escaped_action(self, s, pos, toks):
        if self.debug:
            self.logger.debug(toks[0])
        self.add_part(toks[0], pos, ShToken._ESCAPED)

    def escaped_oct_action(self, s, pos, toks):
        if self.debug:
            self.logger.debug(toks[0])
        self.add_part(toks[0], pos, ShToken._ESCAPED_OCT)

    def escaped_hex_action(self, s, pos, toks):
        if self.debug:
            self.logger.debug(toks[0])
        self.add_part(toks[0], pos, ShToken._ESCAPED_HEX)

    def uq_word_action(self, s, pos, toks):
        if self.debug:
            self.logger.debug(toks[0])
        self.add_part(toks[0], pos, ShToken._UQ_WORD)

    def bq_word_action(self, s, pos, toks):
        if self.debug:
            self.logger.debug(toks[0])
        self.add_part(toks[0], pos, ShToken._BQ_WORD)

    def dq_word_action(self, s, pos, toks):
        if self.debug:
            self.logger.debug(toks[0])
        self.add_part(toks[0], pos, ShToken._DQ_WORD)

    def sq_word_action(self, s, pos, toks):
        if self.debug:
            self.logger.debug(toks[0])
        self.add_part(toks[0], pos, ShToken._SQ_WORD)

    def word_action(self, s, pos, toks):
        if self.debug:
            self.logger.debug(toks[0])

        if self.next_word_type == ShParser._NEXT_WORD_VAL:
            self.parts = ShToken(toks[0], pos, ShToken._WORD, self.parts)
            self.next_word_type = ShParser._NEXT_WORD_CMD
            # self.parts will be reset in assignment_word_action

        elif self.next_word_type == ShParser._NEXT_WORD_CMD:
            pass  # handled by cmd_word_action

        else:
            if self.next_word_type == ShParser._NEXT_WORD_FILE:
                ttype = ShToken._FILE
            else:
                ttype = ShToken._WORD
            self.add_token(toks[0], pos, ttype, self.parts)
            self.parts = []  # reset parts
            self.next_word_type = None

    def cmd_word_action(self, s, pos, toks):
        if self.debug:
            self.logger.debug(toks[0])
        # toks[0] is the whole cmd_word while parts do not include leading modifier if any
        self.add_token(toks[0], pos, ShToken._CMD, self.parts)
        self.next_word_type = None
        self.parts = []

    def punctuator_action(self, s, pos, toks):
        if self.tokens[-1].ttype != ShToken._PUNCTUATOR and self.tokens[-1].spos != pos:
            if self.debug:
                self.logger.debug(toks[0])
            self.add_token(toks[0], pos, ShToken._PUNCTUATOR)
            self.next_word_type = ShParser._NEXT_WORD_CMD

    def pipe_op_action(self, s, pos, toks):
        if self.debug:
            self.logger.debug(toks[0])
        self.add_token(toks[0], pos, ShToken._PIPE_OP)
        self.next_word_type = ShParser._NEXT_WORD_CMD

    def io_redirect_op_action(self, s, pos, toks):
        if self.debug:
            self.logger.debug(toks[0])
        self.add_token(toks[0], pos, ShToken._IO_REDIRECT_OP)
        self.next_word_type = ShParser._NEXT_WORD_FILE

    def add_token(self, tok, pos, ttype, parts=None):
        self.tokens.append(ShToken(tok, pos, ttype, parts))

    def add_part(self, tok, pos, ttype):
        self.parts.append(ShToken(tok, pos, ttype))


# noinspection PyProtectedMember
class ShExpander(object):

    """
    Expand variables, wildcards, escapes, quotes etc. based on parsed results.
    """

    def __init__(self, stash, debug=False):
        self.stash = stash
        self.debug = debug
        self.logger = logging.getLogger('StaSh.Expander')

    def expand(self, line):

        if self.debug:
            self.logger.debug('line: %s' % repr(line))

        # Parse the line
        tokens, parsed = self.stash.runtime.parser.parse(line)

        # History (bang) check
        tokens, parsed = self.history_subs(tokens, parsed)
        # Update the line to the history expanded form
        line = ' '.join(t.tok for t in tokens)

        # alias substitute
        tokens, parsed = self.alias_subs(tokens, parsed)

        pseq_indices = range(0, len(parsed), 2)
        n_pipe_sequences = len(pseq_indices)

        # First yield here to report a summary about incoming commands
        yield line, n_pipe_sequences  # line for history management

        # Start expanding
        idxt = 0
        for ipseq in pseq_indices:
            pseq = parsed[ipseq]

            # TODO: Because of the generator changes, complete_command is not necessary
            # as it simply contains a single pipe_sequence. It can probably be removed
            # for efficiency.
            pipe_sequence = ShPipeSequence()

            for isc in range(0, len(pseq), 2):
                sc = pseq[isc]
                simple_command = ShSimpleCommand()

                for _ in sc.cmd_prefix:
                    t = tokens[idxt]
                    ident = t.tok[0: len(t.tok) - len(t.parts.tok) - 1]
                    val = ' '.join(self.expand_word(t.parts))
                    simple_command.assignments.append(ShAssignment(ident, val))
                    idxt += 1

                if sc.cmd_word:
                    t = tokens[idxt]
                    fields = self.expand_word(t)
                    simple_command.cmd_word = fields[0]

                    if len(fields) > 1:
                        simple_command.args.extend(fields[1:])
                    idxt += 1

                for _ in sc.args:
                    t = tokens[idxt]
                    simple_command.args.extend(self.expand_word(t))
                    idxt += 1

                if sc.io_redirect:
                    io_op = tokens[idxt].tok
                    t = tokens[idxt + 1]
                    fields = self.expand_word(t)
                    if len(fields) > 1:
                        raise ShSingleExpansionRequired('multiple IO file: %s' % fields)
                    simple_command.io_redirect = ShIORedirect(io_op, fields[0])
                    idxt += 2

                # Remove any empty fields after expansion.
                if simple_command.args:
                    simple_command.args = [arg for arg in simple_command.args if simple_command.args]
                if simple_command.cmd_word == '' and simple_command.args:
                    simple_command.cmd_word = simple_command.args.pop(0)
                if simple_command.io_redirect and simple_command.io_redirect.filename == '':
                    raise ShBadSubstitution('ambiguous redirect')

                pipe_sequence.lst.append(simple_command)
                if isc + 1 < len(pseq):
                    idxt += 1  # skip the pipe op

            if ipseq + 1 < len(parsed):
                idxt += 1  # skip the punctuator
                if parsed[ipseq + 1] == '&':
                    pipe_sequence.in_background = True

            # Generator to allow previous command to run first before later command is expanded
            # e.g. A=42; echo $A
            yield pipe_sequence

    def history_subs(self, tokens, parsed):
        history_found = False
        for t in tokens:
            if t.ttype == ShToken._CMD and t.tok.startswith('!'):
                t.tok = self.stash.runtime.search_history(t.tok)
                history_found = True
        if history_found:
            # The line is set to the string with history replaced
            # Re-parse the line
            line = ' '.join(t.tok for t in tokens)
            if self.debug:
                self.logger.debug('history found: %s' % line)
            tokens, parsed = self.stash.runtime.parser.parse(line)
        return tokens, parsed

    def alias_subs(self, tokens, parsed, exclude=None):
        # commands have leading backslash will not be alias is expanded
        # because an alias cannot begin with a backslash and the matching
        # here is done using the whole word of the command, i.e. including
        # any possible leading backslash or bang, e.g. \ls will not match
        # any alias because it is not a valid alias form.
        alias_found = False
        for t in tokens:
            if t.ttype == ShToken._CMD and t.tok in self.stash.runtime.aliases.keys() and t.tok != exclude:
                t.tok = self.stash.runtime.aliases[t.tok][1]
                alias_found = True
        if alias_found:
            # Replace all alias and re-parse the new line
            line = ' '.join(t.tok for t in tokens)
            if self.debug:
                self.logger.debug('alias found: %s' % line)
            tokens, parsed = self.stash.runtime.parser.parse(line)
        return tokens, parsed

    def expand_word(self, word):
        if self.debug:
            self.logger.debug(word.tok)

        words_expanded = []
        words_expanded_globable = []

        w_expanded = w_expanded_globable = ''
        for i, p in enumerate(word.parts):
            if p.ttype == ShToken._ESCAPED:
                ex, exg = self.expand_escaped(p.tok)

            elif p.ttype in [ShToken._ESCAPED_OCT, ShToken._ESCAPED_HEX]:
                ex, exg = self.expand_escaped_oct_or_hex(p.tok)

            elif p.ttype == ShToken._UQ_WORD:
                if i == 0:  # first part in the word
                    ex = exg = self.expand_uq_word(self.expanduser(p.tok))
                else:
                    ex = exg = self.expand_uq_word(p.tok)

            elif p.ttype == ShToken._SQ_WORD:
                ex, exg = self.expand_sq_word(p.tok)

            elif p.ttype == ShToken._DQ_WORD:
                ex, exg = self.expand_dq_word(p.tok)

            elif p.ttype == ShToken._BQ_WORD:
                ret = self.expand_bq_word(p.tok)
                fields = ret.split()
                if len(fields) > 1:
                    words_expanded.append(w_expanded + fields[0])
                    words_expanded.extend(fields[1:-1])
                    words_expanded_globable.append(w_expanded_globable + fields[0])
                    words_expanded_globable.extend(fields[1:-1])
                    w_expanded = w_expanded_globable = ''
                    ex = exg = fields[-1]
                else:
                    ex = exg = ret
            else:
                raise ShInternalError('%s: unknown word parts to expand' % p.ttype)

            w_expanded += ex
            w_expanded_globable += exg

        words_expanded.append(w_expanded)
        words_expanded_globable.append(w_expanded_globable)

        fields = []
        for w_expanded, w_expanded_globable in zip(words_expanded, words_expanded_globable):
            w_expanded_globbed = glob.glob(w_expanded_globable)
            if w_expanded_globbed:
                fields.extend(w_expanded_globbed)
            else:
                fields.append(w_expanded)

        return fields

    def expand_escaped(self, tok):
        # TODO: more escape characters, e.g. ESC
        if self.debug:
            self.logger.debug(tok)

        c = tok[1]
        if c == 't':
            return u'\t', u'\t'
        elif c == 'r':
            return u'\r', u'\r'
        elif c == 'n':
            return u'\n', u'\n'
        elif c in '[]?*':
            return c, u'[%s]' % c
        else:
            return c, c

    def expand_escaped_oct_or_hex(self, tok):
        if self.debug:
            self.logger.debug(tok)

        ret = tok.decode('unicode_escape')
        return ret, ret

    def expand_uq_word(self, tok):
        if self.debug:
            self.logger.debug(tok)
        s = self.expandvars(tok)
        return s

    def expand_sq_word(self, tok):
        if self.debug:
            self.logger.debug(tok)
        return tok[1:-1], self.escape_wildcards(tok[1:-1])

    def expand_dq_word(self, tok):
        if self.debug:
            self.logger.debug(tok)
        parts, parsed = self.stash.runtime.parser.parse_within_dq(tok[1:-1])
        ex = exg = ''
        for p in parts:
            if p.ttype == ShToken._ESCAPED:
                ex1, exg1 = self.expand_escaped(p.tok)

            elif p.ttype in [ShToken._ESCAPED_OCT, ShToken._ESCAPED_HEX]:
                ex1, exg1 = self.expand_escaped_oct_or_hex(p.tok)

            elif p.ttype == ShToken._UQ_WORD:
                ex1 = self.expand_uq_word(p.tok)
                exg1 = self.escape_wildcards(ex1)

            elif p.ttype == ShToken._BQ_WORD:
                ex1 = self.expand_bq_word(p.tok)
                exg1 = self.escape_wildcards(ex1)  # no glob inside dq

            else:
                raise ShInternalError('%s: unknown dq_word parts to expand' % p.ttype)

            ex += ex1
            exg += exg1

        return ex, exg

    def expand_bq_word(self, tok):
        if self.debug:
            self.logger.debug(tok)

        outs = StringIO()
        worker = self.stash.runtime.run(tok[1:-1], final_outs=outs)
        worker.join()
        ret = ' '.join(outs.getvalue().splitlines())
        return ret

    def expanduser(self, s):
        if self.debug:
            self.logger.debug(s)
        saved_environ = os.environ
        try:
            os.environ = self.stash.runtime.envars
            s = os.path.expanduser(s)
            # Command substitution is done by bq_word_action
            # Pathname expansion (glob) is done in word_action
        finally:
            os.environ = saved_environ
        return s

    def expandvars(self, s):
        if self.debug:
            self.logger.debug(s)

        saved_environ = os.environ
        try:
            os.environ = self.stash.runtime.envars

            state = 'a'
            es = ''
            varname = ''
            for nextchar in s:

                if state == 'a':
                    if nextchar == '$':
                        state = '$'
                        varname = ''
                    else:
                        es += nextchar

                elif state == '$':
                    if varname == '':
                        if nextchar == '{':
                            state = '{'
                        elif nextchar in '0123456789@#?':
                            es += str(os.environ.get(nextchar, ''))
                            state = 'a'
                        elif nextchar == '$':
                            es += str(threading.currentThread()._Thread__ident)
                        elif nextchar in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxyz':
                            varname += nextchar
                        else:
                            es += '$' + nextchar
                            state = 'a'

                    else:
                        if nextchar in '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxyz':
                            varname += nextchar
                        else:
                            if self.debug:
                                self.logger.debug('envar sub: %s\n' % varname)
                            es += os.environ.get(varname, '') + nextchar
                            state = 'a'

                elif state == '{':
                    if nextchar == '}':
                        if varname == '':
                            raise ShBadSubstitution('bad envars substitution')
                        else:
                            es += os.environ.get(varname, '')
                            state = 'a'
                    elif nextchar in '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxyz':
                        varname += nextchar
                    else:
                        raise ShBadSubstitution('bad envars substitution')

                else:
                    raise ShInternalError('syntax error in envars substitution')

            if state == '$':
                if varname != '':
                    if self.debug:
                        self.logger.debug('envar sub: %s\n' % varname)
                    es += os.environ.get(varname, '')
                else:
                    es += '$'
            elif state == '{':
                raise ShBadSubstitution('bad envars substitution')

        finally:
            os.environ = saved_environ

        if s != es:
            if self.debug:
                self.logger.debug('expandvars: %s -> %s\n' % (repr(s), repr(es)))

        return es

    def escape_wildcards(self, s0):
        return ''.join(('[%s]' % c if c in '[]?*' else c) for c in s0)


# noinspection PyProtectedMember
class ShCompleter(object):

    """
    This class provides command line auto-completion for the shell.
    """

    def __init__(self, stash, debug=False):
        self.stash = stash
        self.debug = debug
        self.max_possibilities = stash.config.getint('display', 'AUTO_COMPLETION_MAX')
        self.logger = logging.getLogger('StaSh.Completer')

    def complete(self, line):
        """
        Attempt to auto-completes the given line. Returns the completed
        line and a list of possibilities.

        :param str line: The line to complete
        :rtype: (str, [str])
        """
        len_line = len(line)
        try:
            tokens, _ = self.stash.runtime.parser.parse(line)
        except pp.ParseException as e:
            raise ShSyntaxError(e.message)

        toks = []  # this is only for sub-cmd completion
        is_cmd_word = True
        for t in tokens:
            if t.ttype == ShToken._CMD:
                toks = []
                is_cmd_word = True

            if t.epos == len_line:
                word_to_complete = t.tok
                replace_from = t.spos
                break

            toks.append(t.tok)
            is_cmd_word = False

        else:
            word_to_complete = ''
            replace_from = len_line

        toks.append(word_to_complete)

        if self.debug:
            self.logger.debug('is_cmd_word: %s, word_to_complete: %s, replace_from: %d\n' %
                              (is_cmd_word, word_to_complete, replace_from))

        cands, with_normal_completion = self.stash.libcompleter.subcmd_complete(toks)

        if cands is None or with_normal_completion:

            path_names = self.path_match(word_to_complete)

            if is_cmd_word:
                path_names = [p for p in path_names
                              if p.endswith('/') or p.endswith('.py') or p.endswith('.sh')]
                script_names = self.stash.runtime.get_all_script_names()
                script_names.extend(self.stash.runtime.aliases.keys())
                if word_to_complete != '':
                    script_names = [name for name in script_names if name.startswith(word_to_complete)]
            else:
                script_names = []

            if word_to_complete.startswith('$'):
                envar_names = ['$' + varname for varname in self.stash.runtime.envars.keys()
                               if varname.startswith(word_to_complete[1:])]
            else:
                envar_names = []

            all_names = path_names + envar_names + script_names

        else:
            all_names = cands

        all_names = sorted(set(all_names))

        # Do not show hidden files when matching for an empty string
        if word_to_complete == '':
            all_names = [name for name in all_names if not name.startswith('.')]

        # Complete up to the longest common prefix of all possibilities
        prefix = os.path.commonprefix(all_names)

        # TODO: check max number possibilities
        if prefix != '':
            if len(all_names) == 1 and not prefix.endswith('/'):
                prefix += ' '
            newline = line[:replace_from] + prefix
        else:
            newline = line

        return newline, all_names

    def path_match(self, word_to_complete):
        # os.path.xxx functions do not like escaped whitespace
        word_to_complete_normal_whites = word_to_complete.replace('\\ ', ' ')
        full_path = os.path.expanduser(word_to_complete_normal_whites)

        # recognise path with embedded environment variable, e.g. $STASH_ROOT/
        head, tail = os.path.split(word_to_complete_normal_whites)
        if head != '':
            full_path2 = self.stash.runtime.expander.expandvars(full_path)
            if full_path2 != full_path and full_path2 != '':
                full_path = full_path2

        path_names = []
        if os.path.isdir(full_path) and full_path.endswith('/'):
            for fname in os.listdir(full_path):
                if os.path.isdir(os.path.join(full_path, fname)):
                    fname += '/'
                path_names.append(
                    os.path.join(os.path.dirname(word_to_complete), fname.replace(' ', '\\ ')))

        else:
            d = os.path.dirname(full_path) or '.'
            f = os.path.basename(full_path)
            if os.path.isdir(d):
                for fname in os.listdir(d):
                    if fname.startswith(f):
                        if os.path.isdir(os.path.join(d, fname)):
                            fname += '/'
                        path_names.append(
                            os.path.join(os.path.dirname(word_to_complete), fname.replace(' ', '\\ ')))

        return path_names

    def format_all_names(self, all_names):
        # only show the last component to be completed in a directory path
        return '  '.join(os.path.basename(os.path.dirname(name)) + '/' if name.endswith('/')
                         else os.path.basename(name)
                         for name in all_names) + '\n'


class ShThread(threading.Thread):
    """A subclass of threading.Thread, with a kill() method."""

    def __init__(self, name=None, target=None, args=(), kwargs=None, verbose=None):
        super(ShThread, self).__init__(name=name, target=target,
                                       group=None, args=args, kwargs=kwargs, verbose=verbose)
        self.killed = False
        self.child_threads = []

    def start(self):
        """Start the thread."""
        self.__run_backup = self.run
        self.run = self.__run  # Force the Thread to install our trace.
        threading.Thread.start(self)

    def __run(self):
        """Hacked run function, which installs the trace."""
        sys.settrace(self.globaltrace)

        # import cProfile as profile
        # import pstats
        # self._prof = profile.Profile()
        # self._prof.enable()

        self.__run_backup()
        self.run = self.__run_backup

        # self._prof.disable()
        # self.stats = pstats.Stats(self._prof)
        # self.stats.dump_stats(os.path.expanduser('~/Documents/stash-cat.prof'))

    def globaltrace(self, frame, why, arg):
        if why == 'call':
            return self.localtrace
        else:
            return None

    def localtrace(self, frame, why, arg):
        if self.killed:
            if why == 'line':
                for ct in self.child_threads:
                    ct.kill()
                if PYTHONISTA_VERSION == '1.5':
                    raise ShKeyboardInterrupt()
                else:
                    raise KeyboardInterrupt()
        return self.localtrace

    def kill(self):
        self.killed = True


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

        self.enclosed_envars = {}
        self.enclosed_aliases = {}
        self.enclosed_cwd = ''

        self.envars = dict(os.environ,
                           HOME2=os.path.join(os.environ['HOME'], 'Documents'),
                           STASH_ROOT=_STASH_ROOT,
                           BIN_PATH=os.path.join(_STASH_ROOT, 'bin'),
                           PROMPT='[\W]$ ')
        self.aliases = {}
        config = stash.config
        self.rcfile = os.path.join(_STASH_ROOT, _STASH_RCFILE)
        self.historyfile = os.path.join(_STASH_ROOT, _STASH_HISTORY_FILE)
        self.HISTORY_MAX = config.getint('display', 'HISTORY_MAX')

        self.py_traceback = config.getint('system', 'py_traceback')
        self.py_pdb = config.getint('system', 'py_pdb')
        self.input_encoding_utf8 = config.getint('system', 'input_encoding_utf8')
        self.ipython_style_history_search = config.getint('system', 'ipython_style_history_search')

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

        self.enclosing_envars = {}
        self.enclosing_aliases = {}
        self.enclosing_cwd = ''

        self.state_stack = []
        self.worker_stack = []

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
            code_validation_func=None,
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

                    # Parse and expand the line (note this function returns a generator object
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
                            if code_validation_func is None or code_validation_func(pipe_sequence):
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

            except ShKeyboardInterrupt as e:
                self.stash.write_message('^C\nShKeyboardInterrupt:%s\n' % e.message)

            except KeyboardInterrupt as e:
                self.stash.write_message('^C\nKeyboardInterrupt:%s\n' % e.message)

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
                    # self.stash.io.write(self.get_prompt())
                    self.script_will_end()
                self.worker_stack.pop()  # remove itself from the stack

        worker = ShThread(name='_shruntime', target=fn)
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

                    else:
                        self.exec_sh_file(script_file, simple_command_args, ins, outs, errs)

                else:
                    self.envars['?'] = 0

                if self.envars['?'] != 0:
                    break  # break out of the pipe_sequence, but NOT pipe_sequence list

                if isinstance(outs, StringIO):
                    outs.seek(0)  # rewind for next command in the pipe sequence

                prev_outs = outs

            except Exception as e:
                err_msg = '%s\n' % e.message
                if self.debug:
                    self.logger.debug(err_msg)
                self.stash.write_message(err_msg)
                break  # break out of the pipe_sequence, but NOT pipe_sequence list

            finally:
                if type(outs) is file:
                    outs.close()

    def exec_py_file(self, filename, args=None,
                     ins=None, outs=None, errs=None):
        if args is None:
            args = []

        sys.path = _SYS_PATH[:]
        # Add any user set python paths right after the dot or at the begining
        if 'PYTHONPATH' in self.envars.keys():
            try:
                idxdot = sys.path.index('.') + 1
            except ValueError:
                idxdot = 0
            for pth in self.envars['PYTHONPATH'].split(':'):
                sys.path.insert(idxdot, os.path.expanduser(pth))

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

            # If the Exception is a simulated Keyboard Interrupt, the thread
            # can be terminated normally
            if type(e) is ShKeyboardInterrupt:
                self.stash.write_message('^C\nShKeyboardInterrupt:%s\n' % e.message)

            else:
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
                self.exec_sh_lines(fins.readlines(),
                                   ins=ins, outs=outs, errs=errs,
                                   add_to_history=add_to_history)
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

    def exec_sh_lines(self, lines,
                      ins=None, outs=None, errs=None,
                      add_to_history=None):
        worker = self.run(lines,
                          final_ins=ins,
                          final_outs=outs,
                          final_errs=errs,
                          add_to_history=add_to_history,
                          add_new_inp_line=False)
        worker.join()

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


class StaSh(object):
    """
    Main application class. It initialize and wires the components and provide
    utility interfaces to running scripts.
    """

    def __init__(self, debug=(), log_setting=None):

        self.config = self._load_config()
        self.logger = self._config_logging(log_setting)

        # Wire the components
        self.main_screen = ShSequentialScreen(self,
                                              nlines_max=self.config.getint('display', 'BUFFER_MAX'),
                                              debug=_DEBUG_MAIN_SCREEN in debug)

        self.mini_buffer = ShMiniBuffer(self,
                                        self.main_screen,
                                        debug=_DEBUG_MINI_BUFFER in debug)

        self.stream = ShStream(self,
                               self.main_screen,
                               debug=_DEBUG_STREAM in debug)

        self.io = ShIO(self, debug=_DEBUG_IO in debug)

        self.terminal = None  # will be set during UI initialisation
        self.ui = ShUI(self, debug=_DEBUG_UI in debug)
        self.renderer = ShSequentialRenderer(self.main_screen, self.terminal,
                                             debug=_DEBUG_RENDERER in debug)

        parser = ShParser(debug=_DEBUG_PARSER in debug)
        expander = ShExpander(self, debug=_DEBUG_EXPANDER in debug)
        self.runtime = ShRuntime(self, parser, expander, debug=_DEBUG_RUNTIME in debug)
        self.completer = ShCompleter(self, debug=_DEBUG_COMPLETER in debug)

        # Navigate to the startup folder
        if IN_PYTHONISTA:
            os.chdir(self.runtime.envars['HOME2'])
        self.runtime.load_rcfile()
        self.io.write(self.text_style('StaSh v%s\n' % __version__,
                                      {'color': 'blue', 'traits': ['bold']}))
        self.runtime.script_will_end()  # configure the read callback

        # Load shared libraries
        self._load_lib()

        # Register tab handler for running scripts
        self.external_tab_handler = None

    def __call__(self, *args, **kwargs):
        """ This function is to be called by external script for
         executing shell commands """
        worker = self.runtime.run(*args, **kwargs)
        worker.join()

    @staticmethod
    def _load_config():
        config = ConfigParser()
        config.optionxform = str  # make it preserve case
        # defaults
        config.readfp(StringIO(_DEFAULT_CONFIG))
        # update from config file
        config.read(os.path.join(_STASH_ROOT, _STASH_CONFIG_FILE))

        return config

    @staticmethod
    def _config_logging(log_setting):

        logger = logging.getLogger('StaSh')

        _log_setting = {
            'level': 'DEBUG',
            'stdout': True,
        }

        _log_setting.update(log_setting or {})

        level = {
            'CRITICAL': logging.CRITICAL,
            'ERROR': logging.ERROR,
            'WARNING': logging.WARNING,
            'INFO': logging.INFO,
            'DEBUG': logging.DEBUG,
            'NOTEST': logging.NOTSET,
        }.get(_log_setting['level'], logging.DEBUG)

        logger.setLevel(level)

        if not logger.handlers:
            if IN_PYTHONISTA or _log_setting['stdout']:
                _log_handler = logging.StreamHandler(_SYS_STDOUT)
            else:
                _log_handler = logging.handlers.RotatingFileHandler('stash.log', mode='w')
            _log_handler.setLevel(level)
            _log_handler.setFormatter(logging.Formatter(
                '[%(asctime)s] [%(levelname)s] [%(threadName)s] [%(name)s] [%(funcName)s] [%(lineno)d] - %(message)s'
            ))
            logger.addHandler(_log_handler)

        return logger

    def _load_lib(self):
        """
        Load library files as modules and save each of them as attributes
        """
        lib_path = os.path.join(_STASH_ROOT, 'lib')
        saved_environ = dict(os.environ)
        os.environ.update(self.runtime.envars)
        try:
            for f in os.listdir(lib_path):
                if f.startswith('lib') and f.endswith('.py') \
                        and os.path.isfile(os.path.join(lib_path, f)):
                    name, _ = os.path.splitext(f)
                    try:
                        self.__dict__[name] = pyimp.load_source(name, os.path.join(lib_path, f))
                    except Exception as e:
                        self.write_message('%s: failed to load library file (%s)' % (f, repr(e)))
        finally:
            os.environ = saved_environ

    def write_message(self, s):
        self.io.write('stash: %s\n' % s)

    def launch(self, style='panel'):
        self.ui.present(style)
        self.terminal.begin_editing()

    # noinspection PyProtectedMember
    @staticmethod
    def text_style(s, style, always=False):
        """
        Style the given string with ASCII escapes.

        :param str s: String to decorate
        :param dict style: A dictionary of styles
        :param bool always: If true, style will be applied even for pipes.
        :return:
        """
        # No color for pipes
        if not always and (isinstance(sys.stdout, StringIO) or isinstance(sys.stdout, file)):
            return s

        fmt_string = u'%s%%d%s%%s%s%%d%s' % (ctrl.CSI, esc.SGR, ctrl.CSI, esc.SGR)
        for style_name, style_value in style.items():
            if style_name == 'color':
                color_id = graphics._SGR.get(style_value.lower())
                if color_id is not None:
                    s = fmt_string % (color_id, s, graphics._SGR['default'])
            elif style_name == 'bgcolor':
                color_id = graphics._SGR.get('bg-' + style_value.lower())
                if color_id is not None:
                    s = fmt_string % (color_id, s, graphics._SGR['default'])
            elif style_name == 'traits':
                for val in style_value:
                    val = val.lower()
                    if val == 'bold':
                        s = fmt_string % (graphics._SGR['+bold'], s, graphics._SGR['-bold'])
                    elif val == 'italic':
                        s = fmt_string % (graphics._SGR['+italics'], s, graphics._SGR['-italics'])
                    elif val == 'underline':
                        s = fmt_string % (graphics._SGR['+underscore'], s, graphics._SGR['-underscore'])
                    elif val == 'strikethrough':
                        s = fmt_string % (graphics._SGR['+strikethrough'], s, graphics._SGR['-strikethrough'])

        return s

    def text_color(self, s, color_name='default', **kwargs):
        return self.text_style(s, {'color': color_name}, **kwargs)

    def text_bgcolor(self, s, color_name='default', **kwargs):
        return self.text_style(s, {'bgcolor': color_name}, **kwargs)

    def text_bold(self, s, **kwargs):
        return self.text_style(s, {'traits': ['bold']}, **kwargs)

    def text_italic(self, s, **kwargs):
        return self.text_style(s, {'traits': ['italic']}, **kwargs)

    def text_bold_italic(self, s, **kwargs):
        return self.text_style(s, {'traits': ['bold', 'italic']}, **kwargs)

    def text_underline(self, s, **kwargs):
        return self.text_style(s, {'traits': ['underline']}, **kwargs)

    def text_strikethrough(self, s, **kwargs):
        return self.text_style(s, {'traits': ['strikethrough']}, **kwargs)


if __name__ == '__main__':
    _stash = StaSh()
    _stash.launch()