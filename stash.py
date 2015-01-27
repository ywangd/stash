# -*- coding: utf-8 -*-
"""
StaSh - Shell for Pythonista

https://github.com/ywangd/stash
"""
__version__ = '0.4.0'

import ast
import functools
import glob
import os
import string
import sys
import threading
import time
import imp
import argparse

import pyparsing as pp

from ConfigParser import ConfigParser
from StringIO import StringIO

try:
    import ui
    import console
    _IN_PYTHONISTA = True
except ImportError:
    import dummyui as ui
    import dummyconsole as console
    _IN_PYTHONISTA = False


_STDIN = sys.stdin
_STDOUT = sys.stdout
_STDERR = sys.stderr
_SYS_PATH = sys.path
_OS_ENVIRON = os.environ

APP_DIR = os.path.realpath(os.path.abspath(os.path.dirname(__file__)))

_STARTUP_OPTIONS = argparse.Namespace(
    debug_parser=False,
    debug_completer=False,
    debug_runtime=False,
    no_rcfile=False)

def _debug_parser(msg):
    if _STARTUP_OPTIONS.debug_parser:
        _STDOUT.write(msg if msg.endswith('\n') else (msg + '\n'))

def _debug_completer(msg):
    if _STARTUP_OPTIONS.debug_completer:
        _STDOUT.write(msg if msg.endswith('\n') else (msg + '\n'))

def _debug_runtime(msg):
    if _STARTUP_OPTIONS.debug_runtime:
        _STDOUT.write(msg if msg.endswith('\n') else (msg + '\n'))


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

class ShInternalError(Exception):
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

    _NEXT_WORD_CMD = '_NEXT_WORD_CMD'
    _NEXT_WORD_VAL = '_NEXT_WORD_VAL'  # rhs of assignment
    _NEXT_WORD_FILE = '_NEXT_WORD_FILE'

    def __init__(self):

        escaped = pp.Combine("\\" + pp.Word(pp.printables + ' ', exact=1)).setParseAction(self.escaped_action)
        uq_word = pp.Word(_word_chars).setParseAction(self.uq_word_action)
        bq_word = pp.QuotedString('`', escChar='\\', unquoteResults=False).setParseAction(self.bq_word_action)
        dq_word = pp.QuotedString('"', escChar='\\', unquoteResults=False).setParseAction(self.dq_word_action)
        sq_word = pp.QuotedString("'", escChar='\\', unquoteResults=False).setParseAction(self.sq_word_action)
        word = pp.Combine(pp.OneOrMore(escaped ^ uq_word ^ bq_word ^ dq_word ^ sq_word))\
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
        word_in_dq = pp.Combine(pp.OneOrMore(escaped ^ bq_word ^ uq_word_in_dq))
        # ---

        self.parser = complete_command.parseWithTabs().ignore(pp.pythonStyleComment)
        self.parser_within_dq = word_in_dq.leaveWhitespace()
        self.next_word_type = ShParser._NEXT_WORD_CMD
        self.tokens = []
        self.parts = []

    def parse(self, line):
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
        _debug_parser('identifier: %d, %s' % (pos, toks[0]))

    def assign_op_action(self, s, pos, toks):
        _debug_parser('assign_op: %s' % toks[0])
        self.next_word_type = ShParser._NEXT_WORD_VAL

    def assignment_word_action(self, s, pos, toks):
        _debug_parser('assignment_word: %s' % toks[0])
        self.add_token(toks[0], pos, ShToken._ASSIGN_WORD, self.parts)
        self.parts = []
        self.next_word_type = ShParser._NEXT_WORD_CMD

    def escaped_action(self, s, pos, toks):
        _debug_parser('escaped: %s' % toks[0])
        self.add_part(toks[0], pos, ShToken._ESCAPED)

    def uq_word_action(self, s, pos, toks):
        _debug_parser('uq_word: %s' % toks[0])
        self.add_part(toks[0], pos, ShToken._UQ_WORD)

    def bq_word_action(self, s, pos, toks):
        _debug_parser('bq_word: %s' % toks[0])
        self.add_part(toks[0], pos, ShToken._BQ_WORD)

    def dq_word_action(self, s, pos, toks):
        _debug_parser('dq_word: %s' % toks[0])
        self.add_part(toks[0], pos, ShToken._DQ_WORD)

    def sq_word_action(self, s, pos, toks):
        _debug_parser('sq_word: %s' % toks[0])
        self.add_part(toks[0], pos, ShToken._SQ_WORD)

    def word_action(self, s, pos, toks):
        _debug_parser('word: %s' % toks[0])

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
        _debug_parser('cmd_word: %s' % toks[0])
        # toks[0] is the whole cmd_word while parts do not include leading modifier if any
        self.add_token(toks[0], pos, ShToken._CMD, self.parts)
        self.next_word_type = None
        self.parts = []

    def punctuator_action(self, s, pos, toks):
        if self.tokens[-1].ttype != ShToken._PUNCTUATOR and self.tokens[-1].spos != pos:
            _debug_parser('punctuator: %s' % toks[0])
            self.add_token(toks[0], pos, ShToken._PUNCTUATOR)
            self.next_word_type = ShParser._NEXT_WORD_CMD

    def pipe_op_action(self, s, pos, toks):
        _debug_parser('pipe_op: %s' % toks[0])
        self.add_token(toks[0], pos, ShToken._PIPE_OP)
        self.next_word_type = ShParser._NEXT_WORD_CMD

    def io_redirect_op_action(self, s, pos, toks):
        _debug_parser('io_redirect_op: %s' % toks[0])
        self.add_token(toks[0], pos, ShToken._IO_REDIRECT_OP)
        self.next_word_type = ShParser._NEXT_WORD_FILE

    def add_token(self, tok, pos, ttype, parts=None):
        self.tokens.append(ShToken(tok, pos, ttype, parts))

    def add_part(self, tok, pos, ttype):
        self.parts.append(ShToken(tok, pos, ttype))


# noinspection PyProtectedMember
class ShExpander(object):

    def __init__(self, runtime):
        self.runtime = runtime

    def expand(self, line):

        # Parse the line
        tokens, parsed = self.runtime.parser.parse(line)

        # History (bang) check
        tokens, parsed = self.history_subs(tokens, parsed)
        # Update the line to the history expanded form
        line = ' '.join(t.tok for t in tokens)

        # alias substitute
        tokens, parsed = self.alias_subs(tokens, parsed)

        pseq_indices = range(0, len(parsed), 2)
        n_pipe_sequences = len(pseq_indices)
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
                t.tok = self.runtime.search_history(t.tok)
                history_found = True
        if history_found:
            # The line is set to the string with history replaced
            # Re-parse the line
            line = ' '.join(t.tok for t in tokens)
            _debug_parser('history found: %s' % line)
            tokens, parsed = self.runtime.parser.parse(line)
        return tokens, parsed

    def alias_subs(self, tokens, parsed, exclude=None):
        alias_found = False
        for t in tokens:
            if t.ttype == ShToken._CMD and t.tok in self.runtime.aliases.keys() and t.tok != exclude:
                t.tok = self.runtime.aliases[t.tok][1]
                alias_found = True
        if alias_found:
            # Replace all alias and re-parse the new line
            line = ' '.join(t.tok for t in tokens)
            _debug_parser('alias found: %s' % line)
            tokens, parsed = self.runtime.parser.parse(line)
        return tokens, parsed

    def expand_word(self, word):
        _debug_parser('expand_word: %s' % word.tok)

        words_expanded = []
        words_expanded_globable = []

        w_expanded = w_expanded_globable = ''
        for i, p in enumerate(word.parts):
            if p.ttype == ShToken._ESCAPED:
                ex, exg = self.expand_escaped(p.tok)

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
        _debug_parser('expand_escaped: %s' % tok)

        c = tok[1]
        if c == 't':
            return '\t', '\t'
        elif c == 'r':
            return '\r', '\r'
        elif c == 'n':
            return '\n', '\n'
        elif c in '[]?*':
            return c, '[%s]' % c
        else:
            return c, c

    def expand_uq_word(self, tok):
        _debug_parser('expand_uq_word: %s' % tok)
        s = self.expandvars(tok)
        return s

    def expand_sq_word(self, tok):
        _debug_parser('expand_sq_word: %s' % tok)
        return tok[1:-1], self.escape_wildcards(tok[1:-1])

    def expand_dq_word(self, tok):
        _debug_parser('expand_dq_word: %s' % tok)
        parts, parsed = self.runtime.parser.parse_within_dq(tok[1:-1])
        ex = exg = ''
        for p in parts:
            if p.ttype == ShToken._ESCAPED:
                ex1, exg1 = self.expand_escaped(p.tok)

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
        _debug_parser('expand_bq_word: %s' % tok)

        outs = StringIO()
        worker = self.runtime.run(tok[1:-1], final_outs=outs)
        while worker.isAlive():
            pass
        ret = ' '.join(outs.getvalue().splitlines())
        return ret

    def expanduser(self, s):
        _debug_parser('expanduser: %s' % s)
        saved_environ = os.environ
        try:
            os.environ = self.runtime.envars
            s = os.path.expanduser(s)
            # Command substitution is done by bq_word_action
            # Pathname expansion (glob) is done in word_action
        finally:
            os.environ = saved_environ
        return s

    def expandvars(self, s):
        _debug_parser('expandvars: %s' % s)

        saved_environ = os.environ
        try:
            os.environ = self.runtime.envars

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
                        elif nextchar in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxy':
                            varname += nextchar
                        else:
                            es += '$' + nextchar
                            state = 'a'

                    else:
                        if nextchar in '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxy':
                            varname += nextchar
                        else:
                            _debug_parser('envar sub: %s\n' % varname)
                            es += os.environ.get(varname, '') + nextchar
                            state = 'a'

                elif state == '{':
                    if nextchar == '}':
                        if varname == '':
                            raise ShBadSubstitution('bad envars substitution')
                        else:
                            es += os.environ.get(varname, '')
                            state = 'a'
                    elif nextchar in '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxy':
                        varname += nextchar
                    else:
                        raise ShBadSubstitution('bad envars substitution')

                else:
                    raise ShInternalError('syntax error in envars substitution')

            if state == '$':
                if varname != '':
                    _debug_parser('envar sub: %s\n' % varname)
                    es += os.environ.get(varname, '')
                else:
                    es += '$'
            elif state == '{':
                raise ShBadSubstitution('bad envars substitution')

        finally:
            os.environ = saved_environ

        if s != es:
            _debug_parser('expandvars: %s -> %s\n' % (repr(s), repr(es)))

        return es

    def escape_wildcards(self, s0):
        return ''.join(('[%s]' % c if c in '[]?*' else c) for c in s0)


# noinspection PyProtectedMember
class ShCompleter(object):

    def __init__(self, app):
        self.app = app
        self.np_max = app.config.getint('display', 'AUTO_COMPLETION_MAX')

    def complete(self, line, cursor_at=None):
        len_line = len(line)
        try:
            tokens, _ = self.app.runtime.parser.parse(line)
        except pp.ParseException as e:
            self.app.term.write('\n', flush=False)
            self.app.term.write_with_prefix('syntax error: at char %d: %s\n' % (e.loc, e.pstr))
            self.app.term.new_inp_line(with_text=line)
            return

        if cursor_at is None:
            cursor_at = len_line

        toks = []  # this is only for sub-cmd completion
        is_cmd_word = False
        for t in tokens:
            if t.ttype == ShToken._CMD:
                toks = []
                is_cmd_word = True
            toks.append(t.tok)
            if t.spos <= cursor_at <= t.epos:
                word_to_complete = t.tok[:cursor_at]
                toks.pop()
                replace_range = (t.spos, cursor_at)
                break
            is_cmd_word = False
        else:
            word_to_complete = ''
            is_cmd_word = not is_cmd_word
            replace_range = (cursor_at, cursor_at)

        word_to_complete_normal_whites = word_to_complete.replace('\\ ', ' ')

        _debug_completer('is_cmd_word: %s, word_to_complete: %s, replace_range: %s\n' %
                         (is_cmd_word, word_to_complete, repr(replace_range)))

        cands, with_normal_completion = self.app.libcompleter.subcmd_complete(toks, word_to_complete)

        if cands is None or with_normal_completion:

            path_names = self.path_match(word_to_complete_normal_whites)

            if is_cmd_word:
                dirname = os.path.dirname(os.path.expanduser(word_to_complete_normal_whites))
                path_names = [p for p in path_names
                              if os.path.isdir(os.path.join(dirname, p)) or p.endswith('.py') or p.endswith('.sh')]
                script_names = self.app.runtime.get_all_script_names()
                script_names.extend(self.app.runtime.aliases.keys())
                if word_to_complete_normal_whites != '':
                    script_names = [name for name in script_names if name.startswith(word_to_complete_normal_whites)]
            else:
                script_names = []

            if word_to_complete_normal_whites.startswith('$'):
                envar_names = ['$' + varname for varname in self.app.runtime.envars.keys()
                               if varname.startswith(word_to_complete_normal_whites[1:])]
            else:
                envar_names = []

            all_names = path_names + envar_names + script_names

        else:
            all_names = cands

        all_names = sorted(set(all_names))

        if len(all_names) > self.np_max:
            self.app.term.write('\nMore than %d possibilities\n' % self.np_max)
            self.app.term.new_inp_line(with_text=line)
            _debug_completer(self.format_all_names(all_names))

        else:
            # Complete up to the longest common prefix of all possibilities
            prefix = replace_string = os.path.commonprefix(all_names)

            if prefix != '':
                newline = line[:replace_range[0]] + prefix.replace(' ', '\\ ') + line[replace_range[1]:]
            else:
                newline = line

            if newline != line:
                # No need to show available possibilities if some completion can be done
                self.app.term.set_inp_line(newline)
                _debug_completer('%s -> %s' % (repr(line), repr(newline)))

            elif len(all_names) > 0:  # no completion available, show all possibilities if exist
                self.app.term.write('\n%s\n' % self.format_all_names(all_names))
                self.app.term.new_inp_line(with_text=line)
                _debug_completer(self.format_all_names(all_names))

    def path_match(self, word_to_complete_normal_whites):
        full_path = os.path.expanduser(word_to_complete_normal_whites)
        if os.path.isdir(full_path) and full_path.endswith('/'):
            filenames = [(fname + '/') if os.path.isdir(os.path.join(full_path, fname)) else fname
                         for fname in os.listdir(full_path)]
        else:
            d = os.path.dirname(full_path) or '.'
            f = os.path.basename(full_path)
            try:
                filenames = [(fname + '/') if os.path.isdir(os.path.join(full_path, fname)) else (fname + ' ')
                             for fname in os.listdir(d) if fname.startswith(f)]
            except:
                filenames = []
        return filenames

    def format_all_names(self, all_names):
        return '  '.join(all_names) + '\n'


_DEFAULT_RC = r"""
PROMPT='[\W]$ '
BIN_PATH=~/Documents/bin:$BIN_PATH
SELFUPDATE_BRANCH=master
alias env='printenv'
alias logout='echo "Use the close button in the upper right corner to exit StaSh."'
alias help='man'
alias la='ls -a'
alias ll='ls -la'
"""

class ShRuntime(object):

    def __init__(self, app):

        self.app = app

        self.enclosed_envars = {}
        self.enclosed_aliases = {}
        self.enclosed_cwd = ''

        self.envars = dict(os.environ,
                           HOME2=os.path.join(os.environ['HOME'], 'Documents'),
                           STASH_ROOT=APP_DIR,
                           BIN_PATH=os.path.join(APP_DIR, 'bin'))
        self.aliases = {}
        config = app.config
        self.rcfile = os.path.join(APP_DIR, config.get('system', 'rcfile'))
        self.historyfile = os.path.join(APP_DIR, config.get('system', 'historyfile'))
        self.HISTORY_MAX = config.getint('display', 'HISTORY_MAX')

        self.py_traceback = config.getint('system', 'py_traceback')
        self.input_encoding_utf8 = config.getint('system', 'input_encoding_utf8')

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

        self.parser = ShParser()
        self.expander = ShExpander(self)

        self.enclosing_envars = {}
        self.enclosing_aliases = {}
        self.enclosing_cwd = ''

        self.state_stack = []
        self.worker_stack = []

    def save_state(self):

        _debug_runtime('Saving stack %d ----\n' % len(self.state_stack))
        _debug_runtime('envars = %s\n' % sorted(self.envars.keys()))

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

    def restore_state(self,
                      persist_envars=False,
                      persist_aliases=False,
                      persist_cwd=False):

        _debug_runtime('Popping stack %d ----\n' % (len(self.state_stack) - 1))
        _debug_runtime('envars = %s\n' % sorted(self.envars.keys()))

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

        _debug_runtime('After poping\n')
        _debug_runtime('enclosed_envars = %s\n' % sorted(self.enclosing_envars.keys()))
        _debug_runtime('envars = %s\n' % sorted(self.envars.keys()))

    def load_rcfile(self):
        self.app(_DEFAULT_RC.splitlines(), add_to_history=False, add_new_inp_line=False)

        if not _STARTUP_OPTIONS.no_rcfile \
                and os.path.exists(self.rcfile) and os.path.isfile(self.rcfile):
            try:
                with open(self.rcfile) as ins:
                    self.app(ins.readlines(), add_to_history=False, add_new_inp_line=False)
            except IOError:
                self.app.term.write_with_prefix('%s: error reading rcfile\n' % self.rcfile)

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
        """ This function used for completer """
        all_names = []
        for path in ['.'] + self.envars['BIN_PATH'].split(os.pathsep):
            path = os.path.expanduser(path)
            if os.path.exists(path):
                for f in os.listdir(path):
                    if not os.path.isdir(f) and (f.endswith('.py') or f.endswith('.sh')):
                        all_names.append(f)
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
            self.app.term.write_with_prefix('worker threads must be linear\n')

        def fn():
            self.worker_stack.append(threading.currentThread())

            try:
                lines = input_ if type(input_) is list else input_.splitlines()

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
                _debug_parser('ParseException: %s\n' % repr(e))
                self.app.term.write_with_prefix('syntax error: at char %d: %s\n' % (e.loc, e.pstr))

            except ShEventNotFound as e:
                _debug_parser('%s\n' % repr(e))
                self.app.term.write_with_prefix('%s: event not found\n' % e.message)

            except ShBadSubstitution as e:
                _debug_parser('%s\n' % repr(e))
                self.app.term.write_with_prefix('%s\n' % e.message)

            except ShInternalError as e:
                _debug_runtime('%s\n' % repr(e))
                self.app.term.write_with_prefix('%s\n' % e.message)

            except IOError as e:
                _debug_runtime('IOError: %s\n' % repr(e))
                self.app.term.write_with_prefix('%s: %s\n' % (e.filename, e.strerror))

            except Exception as e:
                _debug_runtime('Exception: %s\n' % repr(e))
                self.app.term.write_with_prefix('%s\n' % repr(e))

            finally:
                if add_new_inp_line or (len(self.worker_stack) == 1 and add_new_inp_line is not False):
                    self.app.term.new_inp_line()
                self.app.term.flush()
                self.worker_stack.pop()  # remove itself from the stack

        worker = threading.Thread(name='_shruntime_thread', target=fn)
        worker.start()
        return worker

    def run_pipe_sequence(self, pipe_sequence, final_ins=None, final_outs=None, final_errs=None):
        _debug_runtime(str(pipe_sequence))

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
                    ins = self.app.term

            if not pipe_sequence.in_background:
                outs = self.app.term
                errs = self.app.term
            else:
                outs = _STDOUT
                errs = _STDERR

            if simple_command.io_redirect:
                mode = 'w' if simple_command.io_redirect.operator == '>' else 'a'
                # For simplicity, stdout redirect works for stderr as well.
                # Note this is different from a real shell.
                errs = outs = open(simple_command.io_redirect.filename, mode)

            elif idx < n_simple_commands - 1: # before the last piped command
                outs = StringIO()

            else:
                if final_outs:
                    outs = final_outs
                if final_errs:
                    errs = final_errs

            _debug_runtime('io %s %s\n' % (ins, outs))

            try:
                if simple_command.cmd_word != '':
                    script_file = self.find_script_file(simple_command.cmd_word)

                    _debug_runtime('script is %s\n' % script_file)

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
                _debug_runtime(err_msg)
                self.app.term.write_with_prefix(err_msg)
                break  # break out of the pipe_sequence, but NOT pipe_sequence list

            finally:
                if type(outs) is file:
                    outs.close()

    def exec_py_file(self, filename, args=None,
                     ins=None, outs=None, errs=None):
        if args is None:
            args = []

        # Prepend any user set python paths
        if 'PYTHONPATH' in self.envars.keys():
            sys.path = [os.path.expanduser(pth) for pth in self.envars['PYTHONPATH'].split(':')] + _SYS_PATH

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
            namespace['_stash'] = self.app
            execfile(file_path, namespace, namespace)
            self.envars['?'] = 0

        except SystemExit as e:
            self.envars['?'] = e.code

        except Exception as e:
            if self.py_traceback:
                import traceback
                traceback.print_exc()
            err_msg = '%s: (%s)\n' % (repr(e), sys.exc_value)
            _debug_runtime(err_msg)
            self.app.term.write_with_prefix(err_msg)
            self.envars['?'] = 1

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
            self.app.term.write_with_prefix('%s: %s\n' % (e.filename, e.strerror))
            self.envars['?'] = 1

        except:
            self.app.term.write_with_prefix('%s: error while executing shell script\n' % filename)
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
        while worker.isAlive():
            pass

    def get_prompt(self):
        prompt = self.envars['PROMPT']
        if prompt.find('\\w') or prompt.find('\\W'):
            curdir = os.getcwd().replace(self.envars['HOME'], '~')
            prompt = prompt.replace('\\w', curdir)
            prompt = prompt.replace('\\W',
                                    curdir if os.path.dirname(curdir) == '~' else os.path.basename(curdir))
        return prompt

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
        self.idx_to_history += 1
        if self.idx_to_history >= len(self.history):
            self.idx_to_history -= 1
        else:
            self.app.term.set_inp_line(self.history[self.idx_to_history])

    def history_dn(self):
        self.idx_to_history -= 1
        if self.idx_to_history <= -1:
            self.idx_to_history = -1
        else:
            self.app.term.set_inp_line(self.history[self.idx_to_history])

    def reset_idx_to_history(self):
        self.idx_to_history = -1


class ShVk(ui.View):
    """
    The virtual keyboard container, which implements a swipe cursor positioning gesture
    """
    def __init__(self, app, name='vks', flex='wh'):
        if not _IN_PYTHONISTA:
            super(ShVk, self).__init__()

        self.app = app
        self.flex = flex
        self.name = name
        self.sv = ui.ScrollView(name, flex='wh')
        super(ShVk, self).add_subview(self.sv)
        self.sv.delegate = self
        self.dx = 0

    def layout(self):
        self.sv.content_size = (self.width + 1, self.height)

    def add_subview(self, subview):
        self.sv.add_subview(subview)

    def remove_subview(self, subview):
        self.sv.remove_subview(subview)

    def scrollview_did_scroll(self, scrollview):
        SCROLL_PER_CHAR = 20.0  # Number of pixels to scroll to move 1 character
        # integrate small scroll motions, but keep scrollview from actually moving
        if not scrollview.decelerating:
            self.dx -= scrollview.content_offset[0] / SCROLL_PER_CHAR
        scrollview.content_offset = (0.0, 0.0)

        offset = int(self.dx)
        if offset:
            self.dx -= offset
            self.app.term.set_cursor(offset, whence=1)


class ShTerm(ui.View):
    """
    The View as the terminal of the application
    """

    STREAM = 0
    POOL = 1

    def __init__(self, app):
        if not _IN_PYTHONISTA:
            super(ShTerm, self).__init__()

        self.app = app

        self.mode = ShTerm.STREAM
        self.editing = False
        self.nlines_per_flush_replace = 100
        self.flush_recheck_delay = 0.1  # seconds
        self._flush_thread = None
        self._timer_to_start_flush_thread = None
        self._n_refresh = 8
        self._refresh_pause = 0.01

        self.BUFFER_MAX = app.config.getint('display', 'BUFFER_MAX')
        self.TEXT_FONT = ast.literal_eval(app.config.get('display', 'TEXT_FONT'))
        self.BUTTON_FONT = ast.literal_eval(app.config.get('display', 'BUTTON_FONT'))

        self.vk_symbols = app.config.get('display', 'VK_SYMBOLS')

        self.inp_buf = []
        self.out_buf = ''
        # cursor position count from the end, this is not the same as selected_range[0]
        self.cursor_rindex = None
        self.read_pos = 0
        self.write_pos = 0
        self.input_did_return = False  # For readline, e.g. raw_input
        self.input_did_eof = False  # For read and readlines
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

        self.vks = ShVk(app=app, name='vks', flex='WT')
        self.txts.add_subview(self.vks)
        self.vks.background_color = 0.7

        k_hspacing = 1

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

        self.k_grp_0 = ShVk(app=app, name='k_grp_0', flex='WT')  # vk group 0
        self.vks.add_subview(self.k_grp_0)
        self.k_grp_0.background_color = 0.7
        self.k_grp_0.x = self.k_tab.width + k_hspacing

        self.k_hist = ui.Button(name='k_hist', title=' H ', flex='RTB')
        self.k_grp_0.add_subview(self.k_hist)
        self.k_hist.action = app.vk_tapped
        self.k_hist.font = self.BUTTON_FONT
        self.k_hist.border_width = 1
        self.k_hist.border_color = 0.9
        self.k_hist.corner_radius = 5
        self.k_hist.tint_color = 'black'
        self.k_hist.background_color = 'white'
        self.k_hist.size_to_fit()

        self.k_hup = ui.Button(name='k_hup', title=' Up ', flex='RTB')
        self.k_grp_0.add_subview(self.k_hup)
        self.k_hup.action = app.vk_tapped
        self.k_hup.font = self.BUTTON_FONT
        self.k_hup.border_width = 1
        self.k_hup.border_color = 0.9
        self.k_hup.corner_radius = 5
        self.k_hup.tint_color = 'black'
        self.k_hup.background_color = 'white'
        self.k_hup.size_to_fit()
        self.k_hup.x = self.k_hist.width + k_hspacing

        self.k_hdn = ui.Button(name='k_hdn', title=' Dn ', flex='RTB')
        self.k_grp_0.add_subview(self.k_hdn)
        self.k_hdn.action = app.vk_tapped
        self.k_hdn.font = self.BUTTON_FONT
        self.k_hdn.border_width = 1
        self.k_hdn.border_color = 0.9
        self.k_hdn.corner_radius = 5
        self.k_hdn.tint_color = 'black'
        self.k_hdn.background_color = 'white'
        self.k_hdn.size_to_fit()
        self.k_hdn.x = self.k_hup.x + self.k_hup.width + k_hspacing

        self.k_CD = ui.Button(name='k_CD', title=' CD ', flex='RTB')
        self.k_grp_0.add_subview(self.k_CD)
        self.k_CD.action = app.vk_tapped
        self.k_CD.font = self.BUTTON_FONT
        self.k_CD.border_width = 1
        self.k_CD.border_color = 0.9
        self.k_CD.corner_radius = 5
        self.k_CD.tint_color = 'black'
        self.k_CD.background_color = 'white'
        self.k_CD.size_to_fit()
        self.k_CD.x = self.k_hdn.x + self.k_hdn.width + k_hspacing

        self.k_CC = ui.Button(name='k_CC', title=' CC ', flex='RTB')
        self.k_grp_0.add_subview(self.k_CC)
        self.k_CC.action = app.vk_tapped
        self.k_CC.font = self.BUTTON_FONT
        self.k_CC.border_width = 1
        self.k_CC.border_color = 0.9
        self.k_CC.corner_radius = 5
        self.k_CC.tint_color = 'black'
        self.k_CC.background_color = 'white'
        self.k_CC.size_to_fit()
        self.k_CC.x = self.k_CD.x + self.k_CD.width + k_hspacing

        # Kill line key
        self.k_CU = ui.Button(name='k_CU', title=' CU ', flex='RTB')
        self.k_grp_0.add_subview(self.k_CU)
        self.k_CU.action = app.vk_tapped
        self.k_CU.font = self.BUTTON_FONT
        self.k_CU.border_width = 1
        self.k_CU.border_color = 0.9
        self.k_CU.corner_radius = 5
        self.k_CU.tint_color = 'black'
        self.k_CU.background_color = 'white'
        self.k_CU.size_to_fit()
        self.k_CU.x = self.k_CC.x + self.k_CC.width + k_hspacing

        # End Editing key
        self.k_KB = ui.Button(name='k_KB', title=' KB ', flex='RTB')
        self.k_grp_0.add_subview(self.k_KB)
        self.k_KB.action = app.vk_tapped
        self.k_KB.font = self.BUTTON_FONT
        self.k_KB.border_width = 1
        self.k_KB.border_color = 0.9
        self.k_KB.corner_radius = 5
        self.k_KB.tint_color = 'black'
        self.k_KB.background_color = 'white'
        self.k_KB.size_to_fit()
        self.k_KB.x = self.k_CU.x + self.k_CU.width + k_hspacing

        self.k_swap = ui.Button(name='k_swap', title='..', flex='LTB')
        self.vks.add_subview(self.k_swap)
        self.k_swap.action = app.vk_tapped
        self.k_swap.font = self.BUTTON_FONT
        self.k_swap.border_width = 1
        self.k_swap.border_color = 0.9
        self.k_swap.corner_radius = 5
        self.k_swap.tint_color = 'black'
        self.k_swap.background_color = 'white'
        self.k_swap.size_to_fit()
        self.k_swap.width -= 2
        self.k_swap.x = self.vks.width - self.k_swap.width

        self.k_grp_1 = ShVk(app, name='k_grp_1', flex='WT')  # vk group 1
        self.vks.add_subview(self.k_grp_1)
        self.k_grp_1.background_color = 0.7
        self.k_grp_1.x = self.k_tab.width + k_hspacing

        offset = 0
        for i, sym in enumerate(self.vk_symbols):
            if sym == ' ':
                continue
            if not app.ON_IPAD and i > 7:
                break

            k_sym = ui.Button(name='k_sym', title=' %s ' % sym, flex='RTB')
            self.k_grp_1.add_subview(k_sym)
            k_sym.action = app.vk_tapped
            k_sym.font = self.BUTTON_FONT
            k_sym.border_width = 1
            k_sym.border_color = 0.9
            k_sym.corner_radius = 5
            k_sym.tint_color = 'black'
            k_sym.background_color = 'white'
            k_sym.size_to_fit()
            k_sym.x = offset + k_hspacing * i
            offset += k_sym.width

        self.k_grp_0.width = self.vks.width - self.k_tab.width - self.k_swap.width - 2 * k_hspacing
        self.k_grp_1.width = self.vks.width - self.k_tab.width - self.k_swap.width - 2 * k_hspacing

        self.vks.height = self.k_hist.height
        self.vks.y = self.vks.superview.height - (self.vks.height + 4)

        self.k_grp_1.send_to_back()
        self.on_k_grp = 0

        self.io = ui.TextView(name='io', flex='WH')
        self.txts.add_subview(self.io)
        self.io.height = self.io.superview.height - (self.vks.height + 8)
        self.io.x = 0
        self.io.y = 0
        self.io.auto_content_inset = False
        self.io.content_inset = (0, 0, 0, 0)
        self.io.background_color = ast.literal_eval(app.config.get('display', 'BACKGROUND_COLOR'))
        self.io.indicator_style = app.config.get('display', 'INDICATOR_STYLE')
        self.io.font = self.TEXT_FONT
        self.io.text_color = ast.literal_eval(app.config.get('display', 'TEXT_COLOR'))
        self.io.tint_color = ast.literal_eval(app.config.get('display', 'TINT_COLOR'))
        self.io.autocapitalization_type = ui.AUTOCAPITALIZE_NONE
        self.io.autocorrection_type = False
        self.io.spellchecking_type = False
        self.io.text = ''
        self.io.editable = True
        self.io.delegate = app
        
    def toggle_k_grp(self):
        if self.on_k_grp == 0:
            self.k_grp_1.bring_to_front()
        else:
            self.k_grp_0.bring_to_front()
        self.on_k_grp = 1 - self.on_k_grp
        
    def will_close(self):
        self.cleanup()

    def keyboard_frame_did_change(self, frame):
        if frame[3] > 0:
            self.txts.height = self.height - frame[3]
        else:
            self.txts.height = self.height
        self.flush()

    def read_inp_line(self):
        s = self.out_buf[self.read_pos:]
        return s

    def new_inp_line(self, with_text=''):
        self.seek(0, 2)  # move to the end
        self.prompt = self.app.runtime.get_prompt()
        self.read_pos = self.tell()
        if with_text:
            self.write(self.prompt, flush=False)
            self.set_inp_line(with_text)
        else:
            self.write(self.prompt)

    def set_inp_line(self, s):
        self.write(s, rng=(self.read_pos, len(self.out_buf)), update_read_pos=False)

    def set_read_pos(self, offset, whence=0):
        if whence == 0:  # from start
            self.read_pos = offset
        elif whence == 1:  # current position
            self.read_pos += offset
        elif whence == 2:  # from the end
            self.read_pos = len(self.out_buf) + offset

        if self.read_pos < 0:
            self.read_pos = 0
        elif self.read_pos > len(self.out_buf):
            self.read_pos = len(self.out_buf)

    def set_cursor(self, offset, whence=0):
        # Set cursor position Right Away (without going through the
        # write/flush pipeline)
        if whence == 0:  # from start
            pos = offset
        elif whence == 1:  # current position
            pos = self.io.selected_range[0] + offset
        elif whence == 2:  # from the end
            pos = len(self.out_buf) + offset
        else:
            pos = None

        if pos is not None:
            if pos < self.read_pos:
                pos = self.read_pos
            elif pos > len(self.out_buf):
                pos = len(self.out_buf)
            self.io.replace_range((pos, pos), '')

    def replace_out_buf(self, replacement, rng=None):
        rpl_len = len(replacement)
        # If range is not set, default to replace from the current
        # write position for length of the replacement
        if rng is None:
            rng = (self.write_pos, self.write_pos + rpl_len)
        # If there are more text to the right of the replace bounds,
        # this means we have a replacement in between texts, mark the
        # cursor position so it can be displayed properly later
        if rng[1] < len(self.out_buf):
            self.cursor_rindex = len(self.out_buf) - rng[1]
        else:
            self.cursor_rindex = None
        # The new write position is at the end of the replacement.
        # This is necessary because the string to be replaced may not
        # be the same size as the replacement
        self.write_pos = rng[0] + rpl_len
        # Finally perform the replace
        self.out_buf = self.out_buf[:rng[0]] + replacement + self.out_buf[rng[1]:]

    # file-like methods for output TextView
    def seek(self, offset, whence=0):
        if whence == 0:  # from start
            self.write_pos = offset
        elif whence == 1:  # current position
            self.write_pos += offset
        elif whence == 2:  # from the end
            self.write_pos = len(self.out_buf) + offset

        if self.write_pos < 0:
            self.write_pos = 0
        elif self.write_pos > len(self.out_buf):
            self.write_pos = len(self.out_buf)

    def tell(self):
        return self.write_pos

    def truncate(self, size=None, flush=True):
        if size is None:
            self.out_buf = self.out_buf[0:self.write_pos]
        else:
            self.out_buf = self.out_buf[0:size]
        self.write_pos = self.read_pos = len(self.out_buf)
        if flush:
            self.flush()

    def encode(self, s):
        return s.encode('utf-8') if self.app.runtime.input_encoding_utf8 else s

    # file-like methods (TextField) for IO redirect of external scripts
    # read functions are only called by external script as raw_input
    def read(self, size=-1):
        ret = ''.join(self.readlines())
        if size >= 0:
            ret = ret[:size]
        return ret

    def readline(self, size=-1):  # raw_input
        while not self.input_did_return and not self.input_did_eof:
            pass
        self.input_did_return = self.input_did_eof = False
        # Read from input buffer instead of term directly.
        # This allows the term to response more quickly to user interactions.
        if self.inp_buf:
            line = self.inp_buf.pop()
            line = line[:size] if size >= 0 else line
        else:
            line = '\n'

        return self.encode(line)

    def readlines(self, size=-1):
        while not self.input_did_eof:
            pass
        self.input_did_return = self.input_did_eof = False
        lines = [self.encode(line) for line in self.inp_buf]
        self.inp_buf = []
        if size >= 0:
            lines = lines[:size]
        return lines

    def clear(self):
        self.seek(0)
        self.truncate()
        self.flush()

    def write(self, s, rng=None, update_read_pos=True, flush=True):
        _debug_runtime('Write Called: [%s]\n' % repr(s))
        if not _IN_PYTHONISTA:
            _STDOUT.write(s)
        self.replace_out_buf(s, rng=rng)
        # In most cases, the read position should be the write position.
        # There are cases when read position shouldn't be updated, e.g.
        # when manipulating input line with completer.
        # Also read position can never decrease in a stream like output.
        if update_read_pos and self.write_pos > self.read_pos:
            self.read_pos = self.write_pos
        if flush:
            self.flush()

    def write_with_prefix(self, s, **kwargs):
        self.write('stash: ' + s, **kwargs)

    def writelines(self, lines, **kwargs):
        _debug_runtime('Writeline Called: [%s]\n' % repr(lines))
        self.write(''.join(lines), **kwargs)

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

        if len(lines) > 2 * self.BUFFER_MAX:
            lines = lines[:-self.BUFFER_MAX]
            rng = (0, len(''.join(lines)))
            self.replace_out_buf('', rng=rng)

            self.write_pos -= rng[1]
            if self.write_pos < 0:
                self.write_pos = len(self.out_buf)

            self.read_pos -= rng[1]
            if self.read_pos < 0:
                self.read_pos = len(self.out_buf)

            self.io.text = self.out_buf

        else:
            prefix = os.path.commonprefix([self.out_buf, self.io.text])
            replacement = self.out_buf[len(prefix):]
            rng = (len(prefix), len(self.io.text))
            if replacement == '':
                self.io.replace_range(rng, '')
            else:
                lines = replacement.splitlines(True)
                while lines:
                    self.io.replace_range(rng, ''.join(lines[:self.nlines_per_flush_replace]))
                    lines = lines[self.nlines_per_flush_replace:]
                    rbound = len(self.io.text)
                    rng = (rbound, rbound)

        # Set the cursor position
        if self.cursor_rindex is not None:
            cursor_rindex = len(self.io.text) - self.cursor_rindex
            self.io.replace_range((cursor_rindex, cursor_rindex), '')

        self._scroll_to_end()

    def _scroll_to_end(self, n_refresh=None):
        # Have to scroll multiple times to get the correct scroll to the end effect.
        # This is because content_size reported by the ui system is not reliable.
        # It is either a bug or due to the asynchronous nature of the ui system.
        if self.io.content_size[1] > self.io.height:
            if n_refresh is None:
                n_refresh = self._n_refresh
            for i in range(n_refresh):
                self.io.content_offset = (0, self.io.content_size[1] - self.io.height)
                if i < n_refresh - 1:
                    time.sleep(self._refresh_pause)
              
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
py_traceback=0
input_encoding_utf8=1

[display]
TEXT_FONT=('DejaVuSansMono', 12)
BUTTON_FONT=('DejaVuSansMono', 14)
BACKGROUND_COLOR=(0.0, 0.0, 0.0)
TEXT_COLOR=(1.0, 1.0, 1.0)
TINT_COLOR=(0.0, 0.0, 1.0)
INDICATOR_STYLE=white
HISTORY_MAX=30
BUFFER_MAX=200
AUTO_COMPLETION_MAX=50
VK_SYMBOLS=~/.-*|>$'=!&_"\?`
"""


class StaSh(object):
    """
    The application class, also acts as the controller.
    """

    def __init__(self):

        self.thread = threading.currentThread()

        #TODO: Better way to detect iPad
        self.ON_IPAD = ui.get_screen_size()[1] >= 708

        self.config = self.load_config()
        self.term = ShTerm(self)
        self.runtime = ShRuntime(self)
        self.completer = ShCompleter(self)

        # Navigate to the startup folder
        if _IN_PYTHONISTA:
            os.chdir(self.runtime.envars['HOME2'])
        # parse rc file
        self.runtime.load_rcfile()
        self.term.write('StaSh v%s\n' % __version__)
        self.term.new_inp_line()  # prompt

        # Load library files as modules and save each of them as attributes
        lib_path = os.path.join(APP_DIR, 'lib')
        saved_environ = dict(os.environ)
        os.environ.update(self.runtime.envars)
        try:
            for f in os.listdir(lib_path):
                if f.startswith('lib') and f.endswith('.py') and os.path.isfile(os.path.join(lib_path, f)):
                    name, _ = os.path.splitext(f)
                    try:
                        self.__dict__[name] = imp.load_source(name, os.path.join(lib_path, f))
                    except:
                        self.term.write_with_prefix('%s: failed to load library file' % f)
        finally:
            os.environ = saved_environ

    def __call__(self, *args, **kwargs):
        """ This function is to be called by external script for
         executing shell commands """
        worker = self.runtime.run(*args, **kwargs)
        try:
            while worker.isAlive():
                pass
        except KeyboardInterrupt:  # This is for debug on PC
            self.term.input_did_return = self.term.input_did_eof = True

    @staticmethod
    def load_config():
        config = ConfigParser()
        config.optionxform = str # make it preserve case
        # defaults
        config.readfp(StringIO(_DEFAULT_CONFIG))
        # update from config file
        config.read(os.path.expanduser(config.get('system', 'cfgfile')))
        return config

    def textview_did_begin_editing(self, tv):
        self.term.editing = True

    def textview_did_end_editing(self, tv):
        self.term.editing = False

    def textview_should_return(self, tv):
        if not self.runtime.worker_stack:
            # No thread is running. We are to process the command entered
            # from the GUI.
            line = self.term.read_inp_line()
            self.term.read_pos += len(line)
            if line.strip() != '':
                self.term.inp_buf = []  # clear input buffer for new command
                self.term.input_did_return = False
                self.term.input_did_eof = False
                self.runtime.reset_idx_to_history()
                self.runtime.run(line)
            else:
                self.term.new_inp_line()

        else:
            # we have a running threading, all inputs are considered as
            # directed to the thread, NOT the main GUI program
            s = self.term.read_inp_line()
            self.term.read_pos += len(s)
            self.term.inp_buf.append(s)
            self.term.input_did_return = True

        return True

    def textview_should_change(self, tv, rng, replacement, is_virtual_key=False):
        # do nothing when pressing delete key right before the read position
        if replacement == '' and rng[1] == self.term.read_pos and rng[0] == rng[1] - 1:
            return False

        # If range is invalid, simply append replacement at the end
        saved_rng = rng
        tot_len = len(self.term.out_buf)

        if rng[0] < self.term.read_pos or rng[1] > tot_len:
            rng = (tot_len, tot_len)

        if replacement == '\t':
            self.vk_tapped(self.term.k_tab)

        elif replacement.find('\n') == -1:
            # let valid changes go through the builtin update for performance
            if rng == saved_rng and not is_virtual_key:
                self.term.write(replacement, rng=rng, update_read_pos=False, flush=False)
                return True
            else:
                self.term.write(replacement, rng=rng, update_read_pos=False)

        else:
            trailer = self.term.out_buf[rng[1]:]
            rng = (rng[0], len(self.term.out_buf))
            rpl = replacement.splitlines(True)[0]
            self.term.write(rpl[:-1] + trailer + '\n',
                            rng=rng, update_read_pos=False)
            self.textview_should_return(tv)

        return False

    def textview_did_change(self, tv):
        pass

    def textview_did_change_selection(self, tv):
        # TODO: Possible to support external keyboard arrow keys
        pass
        
    def vk_tapped(self, vk):
        if vk == self.term.k_tab:  # Tab completion
            if not self.runtime.worker_stack:
                rng = self.term.io.selected_range
                cursor_at = None
                # Valid cursor positions are only when non-selection
                # and after the read position
                if rng[0] == rng[1] and rng[0] >= self.term.read_pos:
                    cursor_at = rng[0] - self.term.read_pos
                self.completer.complete(self.term.read_inp_line(), cursor_at=cursor_at)
            else:
                console.hud_alert('Not available', 'error', 1.0)

        elif vk == self.term.k_swap:
            self.term.toggle_k_grp()

        elif vk == self.term.k_hist:
            if not self.runtime.worker_stack:
                self.term.history_present(self.runtime.history_listsource)
            else:
                console.hud_alert('Not available', 'error', 1.0)

        elif vk == self.term.k_hup:
            if not self.runtime.worker_stack:
                self.runtime.history_up()
            else:
                console.hud_alert('Not available', 'error', 1.0)

        elif vk == self.term.k_hdn:
            if not self.runtime.worker_stack:
                self.runtime.history_dn()
            else:
                console.hud_alert('Not available', 'error', 1.0)

        elif vk == self.term.k_CD:
            if self.runtime.worker_stack:
                self.term.input_did_eof = True

        elif vk == self.term.k_CC:
            if not self.runtime.worker_stack:
                self.term.write('\n')
                self.term.write_with_prefix('no thread to terminate\n')
                self.term.new_inp_line()

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
                        self.runtime.restore_state()  # Manually stopped thread does not restore state
                        self.runtime.worker_stack.pop()
                        self.term.write_with_prefix('successfully terminated thread %s\n' % worker)
                self.term.new_inp_line()

        elif vk == self.term.k_KB:
            if self.term.editing:
                self.term.io.end_editing()
            else:
                self.term.io.begin_editing()
                
        elif vk == self.term.k_CU:
            self.term.set_inp_line('')

        elif vk.name == 'k_sym':
            self.textview_should_change(self.term.io,
                                        self.term.io.selected_range,
                                        vk.title.strip(),
                                        is_virtual_key=True)

    def history_popover_tapped(self, sender):
        if sender.selected_row >= 0:
            self.term.set_inp_line(sender.items[sender.selected_row])
            self.runtime.idx_to_history = sender.selected_row

    def will_close(self):
        self.runtime.save_history()

    def run(self):
        self.term.present('panel')
        self.term.io.begin_editing()
   
   
if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Pythonista Shell',
                                 version=__version__)
    ap.add_argument('--debug-parser',
                    action='store_true',
                    help='display parser debugging message'
                    )
    ap.add_argument('--debug-completer',
                    action='store_true',
                    help='display completer debugging message'
                    )
    ap.add_argument('--debug-runtime',
                    action='store_true',
                    help='display runtime debugging message'
                    )
    ap.add_argument('--no-rcfile',
                    action='store_true',
                    help='do not load external resource file')
    ap.parse_args(namespace=_STARTUP_OPTIONS)

    _stash = StaSh()
    _stash.run()

