# -*- coding: utf-8 -*-
"""
StaSh - Shell for Pythonista

https://github.com/ywangd/stash
"""
__version__ = '0.2.0'

import ast
import functools
import glob
import os
import string
import sys
import threading
import time
import imp

import pyparsing as pp

from ConfigParser import ConfigParser
from StringIO import StringIO

try:
    import ui
    import console
    _IN_PYTHONISTA = True
except:
    import dummyui as ui
    import dummyconsole as console
    _IN_PYTHONISTA = False


_STDIN = sys.stdin
_STDOUT = sys.stdout
_STDERR = sys.stderr
_SYS_PATH = sys.path
_OS_ENVIRON = os.environ


_DEBUG_RUNTIME = False
_DEBUG_PARSER = False
_DEBUG_COMPLETER = False


APP_DIR = os.path.realpath(os.path.abspath(os.path.dirname(__file__)))


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
        self.parser_within_dq = word_in_dq
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
        if _DEBUG_PARSER:
            print 'identifier: %d, %s' % (pos, toks[0])

    def assign_op_action(self, s, pos, toks):
        if _DEBUG_PARSER:
            print 'assign_op: %s' % toks[0]
        self.next_word_type = ShParser._NEXT_WORD_VAL

    def assignment_word_action(self, s, pos, toks):
        if _DEBUG_PARSER:
            print 'assignment_word: %s' % toks[0]
        self.add_token(toks[0], pos, ShToken._ASSIGN_WORD, self.parts)
        self.parts = []
        self.next_word_type = ShParser._NEXT_WORD_CMD

    def escaped_action(self, s, pos, toks):
        if _DEBUG_PARSER:
            print 'escaped: %s' % toks[0]
        self.add_part(toks[0], pos, ShToken._ESCAPED)

    def uq_word_action(self, s, pos, toks):
        if _DEBUG_PARSER:
            print 'uq_word: %s' % toks[0]
        self.add_part(toks[0], pos, ShToken._UQ_WORD)

    def bq_word_action(self, s, pos, toks):
        if _DEBUG_PARSER:
            print 'bq_word: %s' % toks[0]
        self.add_part(toks[0], pos, ShToken._BQ_WORD)

    def dq_word_action(self, s, pos, toks):
        if _DEBUG_PARSER:
            print 'dq_word: %s' % toks[0]
        self.add_part(toks[0], pos, ShToken._DQ_WORD)

    def sq_word_action(self, s, pos, toks):
        if _DEBUG_PARSER:
            print 'sq_word: %s' % toks[0]
        self.add_part(toks[0], pos, ShToken._SQ_WORD)

    def word_action(self, s, pos, toks):
        if _DEBUG_PARSER:
            print 'word: %s' % toks[0]

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
        if _DEBUG_PARSER:
            print 'cmd_word: %s' % toks[0]
        # toks[0] is the whole cmd_word while parts do not include leading modifier if any
        self.add_token(toks[0], pos, ShToken._CMD, self.parts)
        self.next_word_type = None
        self.parts = []

    def punctuator_action(self, s, pos, toks):
        if self.tokens[-1].ttype != ShToken._PUNCTUATOR and self.tokens[-1].spos != pos:
            if _DEBUG_PARSER:
                print 'punctuator: %s' % toks[0]
            self.add_token(toks[0], pos, ShToken._PUNCTUATOR)
            self.next_word_type = ShParser._NEXT_WORD_CMD

    def pipe_op_action(self, s, pos, toks):
        if _DEBUG_PARSER:
            print 'pipe_op: %s' % toks[0]
        self.add_token(toks[0], pos, ShToken._PIPE_OP)
        self.next_word_type = ShParser._NEXT_WORD_CMD

    def io_redirect_op_action(self, s, pos, toks):
        if _DEBUG_PARSER:
            print 'io_redirect_op: %s' % toks[0]
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

        yield line  # line for history management

        # alias substitute
        tokens, parsed = self.alias_subs(tokens, parsed)

        # Start expanding
        idxt = 0
        for ipseq in range(0, len(parsed), 2):
            pseq = parsed[ipseq]

            # TODO: Because of the generator changes, complete_command is not necessary
            # as it simply contains a single pipe_sequence. It can probably be removed
            # for efficiency.
            complete_command = ShCompleteCommand()
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
            complete_command.lst.append(pipe_sequence)

            # Generator to allow previous command to run first before later command is expanded
            # e.g. A=42; echo $A
            yield complete_command

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
            if _DEBUG_PARSER:
                print 'history found: %s' % line
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
            if _DEBUG_PARSER:
                print 'alias found: %s' % line
            tokens, parsed = self.runtime.parser.parse(line)
        return tokens, parsed

    def expand_word(self, word):
        if _DEBUG_PARSER:
            print 'expand_word: %s' % word.tok

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
        if _DEBUG_PARSER:
            print 'expand_escaped: %s' % tok

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
        if _DEBUG_PARSER:
            print 'expand_uq_word: %s' % tok
        s = self.expandvars(tok)
        return s

    def expand_sq_word(self, tok):
        if _DEBUG_PARSER:
            print 'expand_sq_word: %s' % tok
        return tok[1:-1], self.escape_wildcards(tok[1:-1])

    def expand_dq_word(self, tok):
        if _DEBUG_PARSER:
            print 'expand_dq_word: %s' % tok
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
        if _DEBUG_PARSER:
            print 'expand_bq_word: %s' % tok

        outs = StringIO()
        worker = self.runtime.run(tok[1:-1], final_outs=outs)
        while worker.isAlive():
            pass
        ret = ' '.join(outs.getvalue().splitlines())
        return ret

    def expanduser(self, s):
        if _DEBUG_PARSER:
            print 'expanduser: %s' % s
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
        if _DEBUG_PARSER:
            print 'expandvars: %s' % s

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
                            if _DEBUG_PARSER:
                                _STDOUT.write('envar sub: %s\n' % varname)
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
                    if _DEBUG_PARSER:
                        _STDOUT.write('envar sub: %s\n' % varname)
                    es += os.environ.get(varname, '')
                else:
                    es += '$'
            elif state == '{':
                raise ShBadSubstitution('bad envars substitution')

        finally:
            os.environ = saved_environ

        if _DEBUG_PARSER:
            if s != es:
                _STDOUT.write('expandvars: %s -> %s\n' % (repr(s), repr(es)))

        return es

    def escape_wildcards(self, s0):
        return ''.join(('[%s]' % c if c in '[]?*' else c) for c in s0)


# noinspection PyProtectedMember
class ShCompleter(object):

    def __init__(self, app):
        self.app = app
        self.np_max = app.config.getint('display', 'AUTO_COMPLETION_MAX')

    def complete(self, line):
        is_cmd_word = False
        has_trailing_white = False
        word_to_complete = word_to_complete_normal_whites = ''

        if line.strip() == '':  # all commands + py files in current directory + all alias
            all_names = self.app.runtime.get_all_script_names()
            all_names.extend(self.app.runtime.aliases.keys())

        else:
            try:
                tokens, _ = self.app.runtime.parser.parse(line)
                if len(line) > tokens[-1].epos:
                    has_trailing_white = True
                word_to_complete = tokens[-1].tok
                word_to_complete_normal_whites = word_to_complete.replace('\\ ', ' ')
                is_cmd_word = tokens[-1].ttype == ShToken._CMD
            except pp.ParseException as e:
                self.app.term.write_with_prefix('syntax error: at char %d: %s\n' % (e.loc, e.pstr))

            if _DEBUG_COMPLETER:
                _STDOUT.write('cmd_word: %s, trailing_white: %s, word_to_complete: %s\n' %
                              (is_cmd_word, has_trailing_white, word_to_complete))

            if has_trailing_white:  # files in current directory
                all_names = [f for f in os.listdir('.')]

            elif is_cmd_word:  # commands match + alias match + path match
                script_names = [script_name for script_name in self.app.runtime.get_all_script_names()
                                if script_name.startswith(word_to_complete_normal_whites)]
                alias_names = [aln for aln in self.app.runtime.aliases.keys()
                               if aln.startswith(word_to_complete_normal_whites)]
                path_names = []
                for p in self.path_match(word_to_complete_normal_whites):
                    if os.path.isdir(os.path.join(os.path.dirname(os.path.expanduser(word_to_complete_normal_whites)), p)) \
                            or p.endswith('.py') or p.endswith('.sh'):
                        path_names.append(p)

                all_names = script_names + alias_names + path_names
            else:  # path match
                all_names = self.path_match(word_to_complete_normal_whites)

            # If the partial word starts with a dollar sign, try envar match
            if word_to_complete_normal_whites.startswith('$'):
                all_names.extend('$' + varname for varname in self.app.runtime.envars.keys()
                                 if varname.startswith(word_to_complete_normal_whites[1:]))

        all_names = sorted(set(all_names))

        if len(all_names) > self.np_max:
            self.app.term.write('%s\nMore than %d possibilities\n'
                                    % (self.app.term.inp.text, self.np_max))
            if _DEBUG_COMPLETER:
                print self.format_all_names(all_names)

        else:
            # Complete up to the longest common prefix of all possibilities
            prefix = replace_string = os.path.commonprefix(all_names)

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
                if os.path.isdir(os.path.expanduser(replace_string)):
                    newline += '/'
                else:
                    newline += ' '

            if newline != line:
                # No need to show available possibilities if some completion can be done
                self.app.term.set_inp_text(newline)  # Complete the line
                if _DEBUG_COMPLETER:
                    print repr(line)
                    print repr(newline)

            elif len(all_names) > 0:  # no completion available, show all possibilities if exist
                self.app.term.write('%s\n%s\n'
                                    % (self.app.term.inp.text, self.format_all_names(all_names)))
                if _DEBUG_COMPLETER:
                    print self.format_all_names(all_names)

    def path_match(self, word_to_complete_normal_whites):
        if os.path.isdir(os.path.expanduser(word_to_complete_normal_whites)) \
                and word_to_complete_normal_whites.endswith('/'):
            filenames = [fname for fname in os.listdir(os.path.expanduser(word_to_complete_normal_whites))]
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

        if _DEBUG_RUNTIME:
            _STDOUT.write('Saving stack %d ----\n' % len(self.state_stack))
            _STDOUT.write('envars = %s\n' % sorted(self.envars.keys()))

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

        if _DEBUG_RUNTIME:
            _STDOUT.write('Popping stack %d ----\n' % (len(self.state_stack) - 1))
            _STDOUT.write('envars = %s\n' % sorted(self.envars.keys()))

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

        if _DEBUG_RUNTIME:
            _STDOUT.write('After poping\n')
            _STDOUT.write('enclosed_envars = %s\n' % sorted(self.enclosing_envars.keys()))
            _STDOUT.write('envars = %s\n' % sorted(self.envars.keys()))

    def load_rcfile(self):
        self.app(_DEFAULT_RC.splitlines(), add_to_history=False)

        if os.path.exists(self.rcfile) and os.path.isfile(self.rcfile):
            try:
                with open(self.rcfile) as ins:
                    self.app(ins.readlines(), add_to_history=False)
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
            reset_inp=None,
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
                    # The first member is the history expanded form
                    newline = expanded.next()
                    # Only add history entry if:
                    #   1. It is explicitly required
                    #   2. It is the first layer thread directly spawned by the main thread
                    #      and not explicitly required to not add
                    if (add_to_history is None and len(self.worker_stack) == 1) or add_to_history:
                        self.add_history(newline)

                    # Subsequent members are actual commands
                    while True:
                        self.save_state()  # State needs to be saved before expansion happens
                        try:
                            complete_command = next(expanded, None)
                            if complete_command is None:  # generator exhausted
                                break

                            if code_validation_func is None or code_validation_func(complete_command):
                                self.run_complete_command(complete_command,
                                                          final_ins=final_ins,
                                                          final_outs=final_outs,
                                                          final_errs=final_errs)
                        finally:
                            self.restore_state(persist_envars=persist_envars,
                                               persist_aliases=persist_aliases,
                                               persist_cwd=persist_cwd)

            except pp.ParseException as e:
                if _DEBUG_PARSER:
                    _STDOUT.write('ParseException: %s\n' % repr(e))
                self.app.term.write_with_prefix('syntax error: at char %d: %s\n' % (e.loc, e.pstr))

            except ShEventNotFound as e:
                if _DEBUG_PARSER:
                    _STDOUT.write('%s\n' % repr(e))
                self.app.term.write_with_prefix('%s: event not found\n' % e.message)

            except ShBadSubstitution as e:
                if _DEBUG_PARSER:
                    _STDOUT.write('%s\n' % repr(e))
                self.app.term.write_with_prefix('%s\n' % e.message)

            except ShInternalError as e:
                if _DEBUG_PARSER or _DEBUG_RUNTIME:
                    _STDOUT.write('%s\n' % repr(e))
                self.app.term.write_with_prefix('%s\n' % e.message)

            except IOError as e:
                if _DEBUG_RUNTIME:
                    _STDOUT.write('IOError: %s\n' % repr(e))
                self.app.term.write_with_prefix('%s: %s\n' % (e.filename, e.strerror))

            except Exception as e:
                if _DEBUG_RUNTIME:
                    _STDOUT.write('Exception: %s\n' % repr(e))
                self.app.term.write_with_prefix('%s\n' % repr(e))

            finally:
                if reset_inp or len(self.worker_stack) == 1:
                    self.app.term.reset_inp()
                self.app.term.flush()
                self.worker_stack.pop()  # remove itself from the stack

        worker = threading.Thread(name='_shruntime_thread', target=fn)
        worker.start()
        return worker

    def run_complete_command(self, complete_command,
                             final_ins=None,
                             final_outs=None,
                             final_errs=None):

        for pipe_sequence in complete_command.lst:
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

    def run_pipe_sequence(self, pipe_sequence, final_ins=None, final_outs=None, final_errs=None):
        if _DEBUG_RUNTIME:
            print pipe_sequence

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

            if _DEBUG_RUNTIME:
                _STDOUT.write('io %s %s\n' % (ins, outs))

            try:
                if simple_command.cmd_word != '':
                    script_file = self.find_script_file(simple_command.cmd_word)

                    if _DEBUG_RUNTIME:
                        _STDOUT.write('script is %s\n' % script_file)

                    if script_file.endswith('.py'):
                        self.exec_py_file(script_file, simple_command.args, ins, outs, errs)

                    else:
                        self.exec_sh_file(script_file, simple_command.args, ins, outs, errs)

                else:
                    self.envars['?'] = 0

                if self.envars['?'] != 0:
                    break  # break out of the pipe_sequence, but NOT pipe_sequence list

                if isinstance(outs, StringIO):
                    outs.seek(0)  # rewind for next command in the pipe sequence

                prev_outs = outs

            except Exception as e:
                err_msg = '%s\n' % e.message
                if _DEBUG_RUNTIME:
                    _STDOUT.write(err_msg)
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
            if _DEBUG_RUNTIME:
                _STDOUT.write(err_msg)
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
                          reset_inp=False)
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
            self.app.term.set_inp_text(self.history[self.idx_to_history])

    def history_dn(self):
        self.idx_to_history -= 1
        if self.idx_to_history <= -1:
            self.idx_to_history = -1
        else:
            self.app.term.set_inp_text(self.history[self.idx_to_history])

    def reset_idx_to_history(self):
        self.idx_to_history = -1


class ShTerm(ui.View):
    """
    The View as the terminal of the application
    """

    def __init__(self, app):
        if not _IN_PYTHONISTA:
            super(ShTerm, self).__init__()

        self.app = app

        self.flush_recheck_delay = 0.1  # seconds
        self._flush_thread = None
        self._timer_to_start_flush_thread = None
        self._n_refresh = 5
        self._refresh_pause = 0.01

        self.BUFFER_MAX = app.config.getint('display', 'BUFFER_MAX')
        self.TEXT_FONT = ast.literal_eval(app.config.get('display', 'TEXT_FONT'))
        self.BUTTON_FONT = ast.literal_eval(app.config.get('display', 'BUTTON_FONT'))

        self.vk_symbols = app.config.get('display', 'VK_SYMBOLS')

        self.inp_buf = []
        self.out_buf = ''
        self.out_buf_pos = 0
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

        self.k_grp_0 = ui.View(name='k_grp_0', flex='WT')  # vk group 0
        self.vks.add_subview(self.k_grp_0)
        self.k_grp_0.background_color = 0.7
        self.k_grp_0.x = self.k_tab.width + k_hspacing

        self.k_hist = ui.Button(name='k_hist', title=' Hist ', flex='RTB')
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

        self.k_CD = ui.Button(name='k_CD', title=' C-D ', flex='RTB')
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

        self.k_CC = ui.Button(name='k_CC', title=' C-C ', flex='RTB')
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

        self.k_swap = ui.Button(name='k_swap', title=' .. ', flex='LTB')
        self.vks.add_subview(self.k_swap)
        self.k_swap.action = app.vk_tapped
        self.k_swap.font = self.BUTTON_FONT
        self.k_swap.border_width = 1
        self.k_swap.border_color = 0.9
        self.k_swap.corner_radius = 5
        self.k_swap.tint_color = 'black'
        self.k_swap.background_color = 'white'
        self.k_swap.size_to_fit()
        self.k_swap.x = self.vks.width - self.k_swap.width

        self.k_grp_1 = ui.View(name='k_grp_1', flex='WT')  # vk group 1
        self.vks.add_subview(self.k_grp_1)
        self.k_grp_1.background_color = 0.7
        self.k_grp_1.x = self.k_tab.width + k_hspacing

        offset = 0
        for i, sym in enumerate(self.vk_symbols):
            if sym == ' ':
                continue
            if not app.ON_IPAD and i > 6:
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

        self.inp = ui.TextField(name='inp', flex='WT')
        self.txts.add_subview(self.inp)
        self.inp.font = self.TEXT_FONT
        self.inp.height = self.TEXT_FONT[1] + 2
        self.inp.y = self.inp.superview.height - (self.inp.height + 4) - (self.vks.height + 4)
        self.inp.background_color = ast.literal_eval(app.config.get('display', 'INPUT_BACKGROUND_COLOR'))
        self.inp.text_color = ast.literal_eval(app.config.get('display', 'INPUT_TEXT_COLOR'))
        self.inp.tint_color = ast.literal_eval(app.config.get('display', 'INPUT_TINT_COLOR'))
        self.inp.text = self.prompt
        self.inp.bordered = False
        self.inp.clear_button_mode = 'always'
        self.inp.autocapitalization_type = ui.AUTOCAPITALIZE_NONE
        self.inp.autocorrection_type = False
        self.inp.spellchecking_type = False
        self.inp.delegate = app

        self.out = ui.TextView(name='out', flex='WH')
        self.txts.add_subview(self.out)
        self.out.height = self.out.superview.height - (self.inp.height + 4) - (self.vks.height + 4)
        self.out.auto_content_inset = False
        self.out.content_inset = (0, 0, -8, 0)
        self.out.background_color = ast.literal_eval(app.config.get('display', 'OUTPUT_BACKGROUND_COLOR'))
        self.out.indicator_style = app.config.get('display', 'OUTPUT_INDICATOR_STYLE')
        self.out.font = self.TEXT_FONT
        self.out.text_color = ast.literal_eval(app.config.get('display', 'OUTPUT_TEXT_COLOR'))
        self.out.tint_color = ast.literal_eval(app.config.get('display', 'OUTPUT_TINT_COLOR'))
        self.out.text = ''
        self.out.editable = False
        self.out.delegate = app
        
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
            self.flush()
        else:
            self.txts.height = self.height

    def read_inp_line(self):
        return self.inp.text[len(self.prompt):]
  
    def reset_inp(self):
        self.set_inp_text('')
  
    def set_inp_text(self, s, with_prompt=True):
        if with_prompt:
            self.prompt = self.app.runtime.get_prompt()
            self.inp.text = '%s%s' % (self.prompt, s)
        else:
            self.inp.text = s
 
    def add_out_buf(self, s):
        """Control the buffer size"""
        if s == '':
            return

        if self.out_buf_pos == len(self.out_buf):
            self.out_buf += s
            self.out_buf_pos = len(self.out_buf)
        else:
            new_pos = self.out_buf_pos + len(s)
            self.out_buf = self.out_buf[0:self.out_buf_pos] + s + self.out_buf[new_pos:]
            self.out_buf_pos = new_pos

    # file-like methods for output TextView
    def seek(self, offset, whence=0):
        if whence == 0:  # from start
            self.out_buf_pos = offset
        elif whence == 1:  # current position
            self.out_buf_pos += offset
        elif whence == 2:  # from the end
            self.out_buf_pos = len(self.out_buf) + offset

        if self.out_buf_pos < 0:
            self.out_buf_pos = 0
        elif self.out_buf_pos > len(self.out_buf):
            self.out_buf_pos = len(self.out_buf)

    def tell(self):
        return self.out_buf_pos

    def truncate(self, size=None):
        if size is None:
            self.out_buf = self.out_buf[0:self.out_buf_pos]
        else:
            self.out_buf = self.out_buf[0:size]

    # file-like methods (TextField) for IO redirect of external scripts
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
        self.seek(0)
        self.truncate()
        self.flush()

    def write(self, s):
        if _DEBUG_RUNTIME:
            _STDOUT.write('Write Called: [%s]\n' % repr(s))
        if not _IN_PYTHONISTA:
            _STDOUT.write(s)
        self.add_out_buf(s)
        self.flush()

    def write_with_prefix(self, s):
        self.write('stash: ' + s)

    def writelines(self, lines):
        if _DEBUG_RUNTIME:
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
AUTO_COMPLETION_MAX=30
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
        self.term.reset_inp()  # prompt

        # Load library files as modules and save each of them as attributes
        lib_path = os.path.join(APP_DIR, 'lib')
        for f in os.listdir(lib_path):
            if f.startswith('lib') and f.endswith('.py') and os.path.isfile(os.path.join(lib_path, f)):
                name, _ = os.path.splitext(f)
                try:
                    self.__dict__[name] = imp.load_source(name, os.path.join(lib_path, f))
                except:
                    self.term.write_with_prefix('%s: failed to load library file' % f)

    def __call__(self, *args, **kwargs):
        """ This function is to be called by external script for
         executing shell commands """
        worker = self.runtime.run(*args, **kwargs)
        while worker.isAlive():
            pass

    @staticmethod
    def load_config():
        config = ConfigParser()
        config.optionxform = str # make it preserve case
        # defaults
        config.readfp(StringIO(_DEFAULT_CONFIG))
        # update from config file
        config.read(os.path.expanduser(config.get('system', 'cfgfile')))
        return config

    def textfield_did_begin_editing(self, textfield):
        pass

    def textfield_did_end_editing(self, textfield):
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
                self.term.input_did_return = False
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

    def textfield_should_change(self, textfield, range_, replacement):
        if not self.runtime.worker_stack:
            if range_[0] < len(self.term.prompt):  # Do not erase the prompt
                return False
        return True

    def textfield_did_change(self, textfield):
        if not self.runtime.worker_stack:
            # Do not wipe prompt (guard against the clear button)
            if len(textfield.text) < len(self.term.prompt):
                self.term.reset_inp()

    def vk_tapped(self, vk):
        if vk == self.term.k_tab:  # Tab completion
            if not self.runtime.worker_stack:
                self.completer.complete(self.term.read_inp_line())
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
                        self.runtime.restore_state()  # Manually stopped thread does not restore state
                        self.runtime.worker_stack.pop()
                        self.term.write_with_prefix('successfully terminated thread %s\n' % worker)
                self.term.reset_inp()
        elif vk.name == 'k_sym':
            # TODO: impossible to detect cursor position?
            self.term.inp.text += vk.title.strip()

    def history_popover_tapped(self, sender):
        if sender.selected_row >= 0: 
            self.term.set_inp_text(sender.items[sender.selected_row])
            self.runtime.idx_to_history = sender.selected_row

    def will_close(self):
        self.runtime.save_history()

    def run(self):
        self.term.present('panel')
        self.term.inp.begin_editing()
   
   
if __name__ == '__main__':
    _stash = StaSh()
    _stash.run()

