# coding: utf-8

import os
import string
import glob
import logging
import threading

from six import StringIO

import pyparsing as pp

from .shcommon import ShSingleExpansionRequired, ShBadSubstitution, ShInternalError


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

cmd_suffix       : word + [io_redirect]
                 | io_redirect

io_redirect      : ('>' | '>>') filename

modifier         : '!' | '\'

cmd_word         : [modifier] word
filename         : word

word             : escaped | uq_word | bq_word | dq_word | sq_word

uq_word          : (WORD_CHARS)+ | '&3'

"""

_WORD_CHARS = string.digits + string.ascii_letters + r'''!#$%()*+,-./:=?@[]^_{}~'''

class ShAssignment(object):
    def __init__(self, identifier, value):
        self.identifier = identifier
        self.value = value

    def __repr2__(self):
        s = '%s=%s' % (self.identifier, self.value)
        return s

    def __repr__(self):
        return self.__repr2__()

class ShIORedirect(object):
    def __init__(self, operator, filename):
        self.operator = operator
        self.filename = filename

    def __repr2__(self):
        ret = '%s %s' % (self.operator, self.filename)
        return ret

    def __repr__(self):
        return self.__repr2__()

class ShSimpleCommand(object):
    def __init__(self):
        self.assignments = []
        self.cmd_word = ''
        self.args = []
        self.io_redirect = None

    def __repr2__(self):
        s = 'assignments: %s\ncmd_word: %s\nargs: %s\nio_redirect: %s\n' % \
            (', '.join(str(asn) for asn in self.assignments),
             self.cmd_word,
             ', '.join(self.args),
             self.io_redirect)
        return s

    def __repr__(self):
        if len(self.assignments) > 0:
            s = ' '.join(str(asn) for asn in self.assignments) + ' ' + self.cmd_word
        else:
            s = self.cmd_word

        if len(self.args):
            s += ' '.join(self.args)

        if self.io_redirect:
            s += ' ' + str(self.io_redirect)
        return s

class ShPipeSequence(object):
    def __init__(self):
        self.in_background = False
        self.lst = []

    def __repr2__(self):
        s = '-------- ShPipeSequence --------\n'
        s += 'in_background: %s\n' % self.in_background
        for idx, cmd in enumerate(self.lst):
            s += '------ ShSimpleCommand %d ------\n%s' % (idx, repr(cmd))
        return s

    def __repr__(self):
        s = ' | '.join(str(cmd) for cmd in self.lst)
        if self.in_background:
            s += ' &'
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
        # Some special uq_word is needed, e.g. &3 for file descriptor of Pythonista interactive prompt
        uq_word = (pp.Literal('&3') | pp.Word(_WORD_CHARS)).setParseAction(self.uq_word_action)
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

    :type stash: StaSh
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

            # Due to the generator change, complete_command is redundant and removed
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
        _, current_state = self.stash.runtime.get_current_worker_and_state()

        alias_found = False
        for t in tokens:
            if t.ttype == ShToken._CMD and t.tok in current_state.aliases.keys() and t.tok != exclude:
                t.tok = current_state.aliases[t.tok][1]
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
        if self.debug:
            self.logger.debug(tok)

        c = tok[1]
        if c == 't':
            return u'\t', u'\t'
        if c == 'b':
            return u'\b', u'\b'
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

        ret = tok.encode('latin-1').decode('unicode_escape')
        # ^^^ no, we can not use utf-8 here
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

        _, current_state = self.stash.runtime.get_current_worker_and_state()
        saved_environ = os.environ
        try:
            os.environ = current_state.environ
            s = os.path.expanduser(s)
            # Command substitution is done by bq_word_action
            # Pathname expansion (glob) is done in word_action
        finally:
            os.environ = saved_environ
        return s

    def expandvars(self, s):
        if self.debug:
            self.logger.debug(s)

        _, current_state = self.stash.runtime.get_current_worker_and_state()
        saved_environ = os.environ
        try:
            os.environ = current_state.environ

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
                            state = 'a'
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
                                self.logger.debug('environ sub: %s\n' % varname)
                            es += os.environ.get(varname, '') + nextchar
                            state = 'a'

                elif state == '{':
                    if nextchar == '}':
                        if varname == '':
                            raise ShBadSubstitution('bad environ substitution')
                        else:
                            es += os.environ.get(varname, '')
                            state = 'a'
                    elif nextchar in '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxyz':
                        varname += nextchar
                    else:
                        raise ShBadSubstitution('bad environ substitution')

                else:
                    raise ShInternalError('syntax error in environ substitution')

            if state == '$':
                if varname != '':
                    if self.debug:
                        self.logger.debug('environ sub: %s\n' % varname)
                    es += os.environ.get(varname, '')
                else:
                    es += '$'
            elif state == '{':
                raise ShBadSubstitution('bad environ substitution')

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
        _, current_state = self.stash.runtime.get_current_worker_and_state()

        len_line = len(line)
        tokens, _ = self.stash.runtime.parser.parse(line)

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
                script_names.extend(current_state.aliases.keys())
                if word_to_complete != '':
                    script_names = [name for name in script_names if name.startswith(word_to_complete)]
            else:
                script_names = []

            if word_to_complete.startswith('$'):
                environ_names = ['$' + varname for varname in current_state.environ.keys()
                               if varname.startswith(word_to_complete[1:])]
            else:
                environ_names = []

            all_names = path_names + environ_names + script_names

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