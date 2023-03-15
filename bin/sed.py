#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals
from io import open, StringIO, BytesIO
from tempfile import NamedTemporaryFile

import argparse
import codecs
import locale
import os
import re
import sys
import traceback
import webbrowser


__updated__ = '2021-05-21 19:14:11'

BRIEF = """
sed.py - python sed module and command line utility\
"""
VERSION = '2.00'
COPYRIGHT = """
Copyright (c) 2021 Frank Schaeckermann
    (github dash fschaeckermann at snkmail dot com)'
Copyright (c) 2014 Gilles Arcas-Luque
    (gilles dot arcas at gmail dot com)
"""
DESCRIPTION = """\
This module implements a GNU sed version 4.8 compatible sed command and module.
This version is a major overhaul by Frank Schaeckermann of the original code
done by Gilles Arcas-Luque.
All missing sed command line options (based on GNU sed version 4.8) where
added, together with some further enhancements:
- restructured the code to be object-oriented through and through
- allows for multiple input files and multiple script-parts (-e and -f)
- inplace editing
- added all the documented backslash-escapes
- allow for much more powerful Python-syntax in regexp (-p or --python-syntax)
- added very detailed error handling with appropriate messages pointing at the
  exact script source location of the error
- supports \\L \\U \\l \\u and \\E in the replacement string
Things not working like in GNU sed version 4.8 are
- no support for character classes like [:lower:] due to missing support for
  them in Pyhton regular expressions (anybody having a list of all lower case
  unicode characters?)
- the e command is not implemented
These are the only two tests of the test suites contained in the project, that
fail. All other tests pass - including using newline as a delimiter for the s
command.
"""
LICENSE = """\
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

DEFAULT_ENCODING = locale.getpreferredencoding()
PY2 = sys.version_info[0] == 2
if PY2:

    def make_unicode(strg, encoding):
        if type(strg) == str:
            return unicode(strg, encoding)
        else:
            return strg

else:
    class unicode(object):  # pragma: no cover @ReservedAssignment
        pass

    def make_unicode(strg, encoding):  # @UnusedVariable
        if type(strg) == bytes:
            return strg.decode(encoding)
        else:
            return strg

    def unichr(char):  # @ReservedAssignment
        return chr(char)


DEBUG_ENCODING = DEFAULT_ENCODING


def DEBUG(text, **kwargs):
    sys.stderr.write(text.format(**kwargs)+'\n')


class ScriptLine (object):
    debug = 0

    def __init__(self,
                 encoding=DEFAULT_ENCODING,
                 line=None,
                 lineno=0,
                 scriptIdx=0,
                 sourceIdx=0,
                 source=None):
        self.encoding = encoding
        if line is not None:
            self.line = make_unicode(line, encoding)
            while self.line.endswith('\n'):
                self.line = self.line[0:-1]
            if self.line.endswith('\\'):
                self.is_continued = True
                self.line = self.line[0:-1]  # remove continuation character
            else:
                self.is_continued = False
            self.line += '\n'  # and add back the escaped new line character
            self.pos = 0
            self.next = None
            if type(source) == int:
                src = '-e #{}'.format(source)
            elif source is None:
                src = 'stream #{}'.format(sourceIdx)
            else:
                src = '-f {}'.format(source)
            self.source = src + ' line {}'.format(lineno)
            self.scriptIdx = scriptIdx
            self.last_char = ' '
            self.last_pos = -1
            self.last_source = self.source

    @property
    def position(self):
        return self.last_source + ' char ' + str(self.last_pos + 1)

    def copy(self):
        new = ScriptLine()  # create empty object to be filled directly
        new.encoding = self.encoding
        new.line = self.line
        new.is_continued = self.is_continued
        new.pos = self.pos
        new.next = self.next
        new.source = self.source
        new.scriptIdx = self.scriptIdx
        new.last_char = self.last_char
        new.last_pos = self.last_pos
        new.last_source = self.last_source
        return new

    def become(self, scriptLine):
        self.encoding = scriptLine.encoding
        self.line = scriptLine.line
        self.is_continued = scriptLine.is_continued
        self.pos = scriptLine.pos
        self.next = scriptLine.next
        self.source = scriptLine.source
        self.scriptIdx = scriptLine.scriptIdx
        # we do not override last_char, last_pos nor last_source!

    def add_next(self, scriptLine):
        self.next = scriptLine
        return scriptLine

    def _printable(self, char_or_string_or_string_list):
        if type(char_or_string_or_string_list) in [list, tuple]:
            if len(char_or_string_or_string_list) == 0:
                return '[]'
            result = '['
            for string in char_or_string_or_string_list:
                result += self._printable(string)+', '
            return result[:-2]+']'
        elif len(char_or_string_or_string_list) > 1:
            result = u"'"
            for char in char_or_string_or_string_list:
                result += self._printable(char)
            return result+u"'"
        else:
            char_ord = ord(char_or_string_or_string_list)
            if char_ord < 0x20 or 0x7f <= char_ord <= 0x9f:
                return '\\x{ord:02x}'.format(ord=char_ord)
            return char_or_string_or_string_list

    def get_char(self):
        self.last_source = self.source
        self.last_pos = self.pos
        if self.pos < len(self.line):
            char = self.line[self.pos]
            self.pos += 1
            self.last_char = char
            if self.pos == len(self.line) and self.is_continued:
                self.become(self.next)
            if self.debug >= 3:
                DEBUG('get_char returning "{chr}" from {pos}',
                      chr=self._printable(char),
                      pos=self.position)
            return char
        self.last_char = '\0'
        if self.debug >= 3:
            DEBUG('get_char returning \\x00 from {pos}', pos=self.position)
        return '\0'

    def continue_on_next_line(self):
        if self.pos == len(self.line) and self.next:
            if self.debug >= 3:
                DEBUG('continue_on_next_line: switching to next line')
            self.become(self.next)
        elif self.debug >= 3:
            DEBUG('continue_on_next_line: not switching to next line')

    def look_ahead(self, *args):
        for i in range(len(args)):
            if self.pos+i >= len(self.line) or self.line[self.pos+i] not in args[i]:
                if self.debug >= 3:
                    DEBUG('look_ahead returning False for {args} at {pos}',
                          args=self._printable(args),
                          pos=self.position)
                return False
        if self.debug >= 3:
            DEBUG('look_ahead returning True for {args} at {pos}',
                  args=self._printable(args),
                  pos=self.position)
        return True

    def get_non_space_char_within_current_line(self):
        if self.debug >= 3:
            DEBUG('get_non_space_char_within_current_line entered')
        char = self.get_char()
        while char != '\n' and char.isspace():
            char = self.get_char()
        if self.debug >= 3:
            DEBUG('get_non_space_char_within_current_line returning {chr} from {pos}',
                  chr=self._printable(char),
                  pos=self.position)
        return char

    def get_non_space_char_within_continued_lines(self):
        if self.debug >= 3:
            DEBUG('get_non_space_char_within_continued_lines entered')
        char = self.get_char()
        while char.isspace():
            char = self.get_char()
        if self.debug >= 3:
            DEBUG('get_non_space_char_within_continued_lines returning {chr} from {pos}',
                  chr=self._printable(char),
                  pos=self.position)
        return char

    def skip_space_within_continued_lines(self):
        if self.debug >= 3:
            DEBUG('skip_space_within_continued_lines entered')
        char = self.last_char
        while char.isspace():
            char = self.get_char()
        if self.debug >= 3:
            DEBUG('skip_space_within_continued_lines returning {chr} from {pos}',
                  chr=self._printable(char),
                  pos=self.position)
        return char

    def skip_over_end_of_cmd(self):
        if self.debug >= 3:
            DEBUG('skip_over_end_of_cmd entered')
        char = self.last_char
        if char == '\0' or char.isspace():
            char = self.get_non_space_char_within_continued_lines()
        while (char == '\0' or char == '#' or char == ';'):
            if char == '\0':
                if self.next is not None:
                    self.become(self.next)
                else:
                    return char
            elif char == '#':
                self.pos = len(self.line)  # skip to end of line
            char = self.get_non_space_char_within_continued_lines()
        if self.debug >= 3:
            DEBUG('skip_over_end_of_cmd returning {chr} from {pos}',
                  chr=self._printable(char),
                  pos=self.position)
        return char

    def is_end_of_cmd(self):
        if self.debug >= 3:
            DEBUG('is_end_of_cmd entered')
        char = self.last_char
        if char.isspace():
            char = self.get_non_space_char_within_continued_lines()
        if self.debug >= 3:
            DEBUG('is_end_of_cmd returning {bool}', bool=(char in ';#}\0'))
        return char in ';#}\0'  # block-end is implicit eoc


PLACE_NOESCAPE = 0
PLACE_TEXT = 1
PLACE_REPL = 2
PLACE_REGEXP = 4
PLACE_CHRSET = 8
PLACE_NAMES = {
        PLACE_TEXT: 'normal text',
        PLACE_REPL: 'replacement',
        PLACE_REGEXP: 'regular expression',
        PLACE_CHRSET: 'character set',
    }


class Script(object):

    def __init__(self, sed):
        # we need this for access to configuration
        self.sed = sed
        self.needs_last_line = False
        self.first_line = None
        self.last_line = None
        self.script_line = None
        self.obj_idx = 0
        self.strg_idx = 0
        self.file_idx = 0
        self.script_idx = 0
        self.referenced_labels = {}
        self.defined_labels = {}
        self.started_blocks = []
        self.first_command_entry = None
        self.cmd_idx = 0

    def __str__(self):
        if self.first_command_entry is None:  # pragma: no cover  (only used within IDE)
            return '<nothing compiled yet>'
        result = ''
        command = self.first_command_entry
        while command:
            result += str(command) + '\n'
            if command.function == '{':
                command = command.branch
            else:
                command = command.next
        return result

    def command_index(self):
        self.cmd_idx += 1
        return self.cmd_idx

    # convenience methods that are
    # all delegated to script_line
    @property
    def position(self):
        return self.script_line.position

    def get_char(self):
        return self.script_line.get_char()

    def get_non_space_char_within_current_line(self):
        return self.script_line.get_non_space_char_within_current_line()

    def get_non_space_char_within_continued_lines(self):
        return self.script_line.get_non_space_char_within_continued_lines()

    def skip_space_within_continued_lines(self):
        return self.script_line.skip_space_within_continued_lines()

    def look_ahead(self, *args):
        return self.script_line.look_ahead(*args)

    # methods to add script content
    def add_string(self, strg, encoding):
        self.script_idx += 1
        self.strg_idx += 1
        lineno = 0
        unicode_strg = make_unicode(strg, encoding)
        for line in unicode_strg.split('\n'):
            lineno += 1
            self._add(ScriptLine(
                          encoding,
                          line,
                          lineno,
                          self.script_idx,
                          self.strg_idx,
                          self.strg_idx))
        # no continuation check here, since the
        # commands a, i and c can span multiple
        # strings

    def add_file(self, filename, encoding):
        self.script_idx += 1
        self.file_idx += 1
        lineno = 0
        filename = make_unicode(filename, sys.getfilesystemencoding())
        if not os.path.exists(filename):
            raise SedException('', 'Script file {file} does not exist.', file=filename)
        try:
            with open(filename, 'rt', encoding=encoding) as f:
                for line in f.readlines():
                    lineno += 1
                    self._add(ScriptLine(
                                    encoding,
                                    line,
                                    lineno,
                                    self.script_idx,
                                    self.file_idx,
                                    filename))
        except IOError as e:  # pragma: no cover
            raise SedException('', 'Error reading script file {file}: {err}',
                               file=filename, err=str(e))
        # if last line is continued, add another
        # empty line to resolve continuation
        if self.last_line.is_continued:
            self._add(ScriptLine(encoding, '\n', lineno + 1,
                                 self.script_idx, self.file_idx, None))

    def add_object(self, script_stream, encoding):
        self.script_idx += 1
        self.obj_idx += 1
        lineno = 0
        for line in script_stream.readlines():
            lineno += 1
            self._add(ScriptLine(
                            encoding,
                            line,
                            lineno,
                            self.script_idx,
                            self.obj_idx,
                            None))
        # if last line is continued, add another
        # empty line to resolve continuation
        if self.last_line.is_continued:
            self._add(ScriptLine(encoding, '\n', lineno + 1,
                                 self.script_idx, self.obj_idx, None))

    def _add(self, script_line):
        self.first_command_entry = None
        if self.last_line:
            self.last_line = self.last_line.add_next(script_line)
        else:
            self.first_line = script_line
            self.last_line = script_line

    def _check_continuation(self):
        if self.last_line.is_continued:
            raise SedException(self.last_line.source,
                               'Invalid line continuation on last script line')

    def get_first_command(self):
        if self.first_command_entry is None:
            self.compile()
        return self.first_command_entry

    # methods to parse and compile the script
    def compile(self):
        if not self.first_line:
            raise SedException('', 'No script specified.')
        self._check_continuation()  # in case the last -e ended in continuation
        ScriptLine.debug = self.sed.debug
        self.referenced_labels = {}
        self.defined_labels = {}
        self.started_blocks = []
        self.parse_flags()
        self.first_command_entry = None
        last_command = None
        self.script_line = self.first_line.copy()
        command = self.get_command()
        while command is not None:
            if self.sed.debug >= 2:
                DEBUG('{cmd}', cmd=command)
            if not last_command:
                self.first_command_entry = command
            else:
                last_command.next = command
            last_command = command
            command = self.get_command()
        if len(self.started_blocks) > 0:
            raise SedException('', 'Unclosed blocks starting at {blockpos}',
                               blockpos=', '.join(b.position for b in
                                                  self.started_blocks))
        if len(self.referenced_labels) > 0:
            raise SedException('', 'Undefined labels referenced:\n    {lbls}',
                               lbls='\n    '
                               .join('{} at {}'
                                     .format(ref.label, ref.position)
                                     for (_, ref_list) in
                                     sorted(self.referenced_labels.items())
                                     for ref in ref_list))

    def parse_flags(self):
        # get flags from first line of script
        if self.first_line.line:
            flags = (self.first_line.line.strip() + '   ')[0:3].strip()
            if flags in ['#n', '#nr', '#rn']:
                self.sed.no_autoprint = True
            if flags in ['#r', '#nr', '#rn']:
                self.sed.regexp_extended = True

    def get_command(self):
        position, addr_range, function = self.get_address()
        # function is the first char after address range.
        # '' if not found and None at script end
        if function == '' or function == '\n' or function == '\0':
            raise SedException(position, 'Address without a command')
        if function is None:
            return None
        else:
            return Command.factory(self, addr_range, function)

    def get_char_list(self, delim):
        u""" this parses a list of characters for the y command """
        strg = ''
        unescstrg = ''
        char = self.get_char()
        while char != '\0' and char != delim:
            if char == '\\':
                if self.look_ahead(delim):
                    char = self.get_char()
                    unesc = char
                else:
                    char, _, unesc = self.get_escape(PLACE_TEXT)
            else:
                unesc = char
            strg += char
            unescstrg += unesc
            char = self.get_char()
        return char, strg, unescstrg

    def get_name(self, kind, alpha_only=True, skip_space=False):
        nme = ''
        if skip_space:
            char = self.get_non_space_char_within_continued_lines()
        else:
            char = self.get_char()
        while (char not in '\0;#}' and
               (char.isalpha() or not (char.isspace() or alpha_only))):
            if char == '\\':
                raise SedException(self.position,
                                   'No backslash escapes allowed in {kind} name.',
                                   kind=kind)
            nme += char
            char = self.get_char()
        return char, nme

    def get_unicode_name(self):
        nme = ''
        char = self.get_char()
        while char not in '\n\0;#}':
            if char == '\\':
                raise SedException(self.position,
                                   'No backslash escapes allowed in unicode character name.')
            nme += char
            char = self.get_char()
        return char, nme

    def get_number(self, first_digit=None):
        if first_digit is None:
            char = self.get_char()
        else:
            char = first_digit
        if char not in '0123456789':
            raise SedException(self.position, 'Expected number')
        num = 0
        while char in '0123456789':
            num = num * 10 + int(char)
            char = self.get_char()
        return char, num

    def get_to_line_end(self):
        result = ''
        char = self.get_non_space_char_within_current_line()
        if char == '\n':
            # there was no non-space character on the current line
            # but it has a continuation on the next line.
            char = self.get_char()
        while char != '\0':
            if char == '\\':
                _, _, unesc = self.get_escape(PLACE_TEXT)
                char = unesc
            result += char
            char = self.get_char()
        if result.endswith('\n'):
            result = result[:-1]  # remove possibly trailing new line
        return result

    def get_escape(self, place):
        """
        places: 1 normal text
                2 replacement
                4 regexp
                8 charset
        sed: 12: \\s \\S \\w \\W
              4: \\b \\B \\< \\> \\<backtic> \\<forwardtic>
              2: \\E \\U \\u \\L \\l
              6: \\1..\\9
             15: \\a \\f \\n \\r \\t \\v \\
             15: \\cx \\d### \\o### \\x##
        py:  12: \\w \\W \\s \\S \\d \\D
              4: \\b \\B \\A \\Z
              6: \\1..\\9 \\10..\\99
             15: \\a \\f \\n \\r \\t \\v \\
             15: \\0 \\01..\\07 \\001..\\377 \\x##
             15: \\u#### \\U######## \\N{name}
         returns (original string, python string, unescaped character
                  - or None for functional escapes)
        """
        pos = self.position
        if place == PLACE_CHRSET:
            # if the backslash is not escaping something, it stands for itself
            # (no need to double it in this case)
            if not self.look_ahead('afnrtvsSwW0cdox' if self.sed.sed_compatible else
                                   'afnrtvsSwW0123xdDuUN'):
                return '\\', '\\\\', '\\'
        char = self.get_char()
        # first the stuff that is the same for both
        if char == 'a':
            return '\\a', '\\a', '\a'
        elif char == 'f':
            return '\\f', '\\f', '\f'
        elif char == 'n':
            return '\\n', '\\n', '\n'
        elif char == 'r':
            return '\\r', '\\r', '\r'
        elif char == 't':
            return '\\t', '\\t', '\t'
        elif char == 'v':
            return '\\v', '\\v', '\v'
        elif char == '\\':
            return '\\\\', '\\\\', '\\'
        elif (place & (PLACE_REGEXP + PLACE_CHRSET)
                and char in 'sSwW'
              or place & PLACE_REGEXP and char in 'bB'):
            char = '\\' + char
            return char, char, None
        elif place == PLACE_REPL and char in 'lLuUE':
            # \\u and \\U collides with Python unicode
            # escapes, but for replacement strings
            # modifying case is more important
            return '\\' + char, '\\' + char, None
        if self.sed.sed_compatible:
            if place == PLACE_REGEXP:
                if char == '\u0060':
                    return '\\\u0060', '\\A', None
                elif char == '\u00B4':
                    return '\\\u00B4', '\\Z', None
                elif char == '<':
                    return '\\<', '(?:\\b(?=\\w))', None
                elif char == '>':
                    return '\\>', '(?:\\b(?=\\W))', None
            if place & (PLACE_REGEXP + PLACE_REPL):
                if char.isdigit() and char != '0':  # group backreference?
                    return '\\' + char, '(?:\\' + char + ')', None
            if char == 'c':
                char = self.get_char()
                if char == '\\':
                    raise SedException(
                        self.script_line.position,
                        'Recursive escaping after \\c not allowed')
                if char.islower():
                    char_ord = ord(char.upper()) ^ 64
                else:
                    char_ord = ord(char) ^ 64
                char = '\\c' + char
                return (char,
                        '\\x'+format(char_ord, '02x'),
                        unichr(char_ord))
            # now we deal with byte escapes of which multiple in a row
            # may actually form a multi-byte character in the chosen
            # encoding and thus must all be processed together to be
            # able to decode it into unicode.
            # This is only done for sed compatible scripts. In Python
            # syntax, the according unicode-escape sequences \\u, \\U
            # or \\N must be used instead.
            strg = ''
            pystrg = ''
            unesc = bytearray()
            while char in 'dox0':
                if char == 'd':
                    num = self.get_char()+self.get_char()+self.get_char()
                    base = 10
                elif char == 'o':
                    num = self.get_char()+self.get_char()+self.get_char()
                    base = 8
                elif char == 'x':
                    num = self.get_char()+self.get_char()
                    base = 16
                else:
                    num = '0'
                    base = 10
                try:
                    int_num = int(num, base)
                except ValueError:
                    raise SedException(
                        pos,
                        'Invalid byte escape \\{chr}{num}. Number is not of base {base}.',
                        chr=char, num=num, base=base)
                strg += '\\'+char+num
                pystrg += '\\x'+format(int_num, '02x')
                unesc.append(int_num)
                try:
                    # let's try if we can decode this to unicode yet
                    return strg, pystrg, unesc.decode(self.script_line.encoding)
                except UnicodeDecodeError:
                    # we do not have enough bytes yet, let's check if there is more available
                    if self.look_ahead('\\', 'dox0'):
                        char = self.get_char()  # get \\
                        char = self.get_char()  # get escaped character
                    else:
                        # no more byte escapes available... report error
                        raise SedException(
                            pos,
                            'Incomplete byte escape data for a valid character in encoding {enc}',
                            enc=self.script_line.encoding)
        else:
            if (char in 'AZ' and place == PLACE_REGEXP  # noqa: E127
                  or char in 'dD' and place & (PLACE_REGEXP + PLACE_CHRSET)):
                char = '\\' + char
                return char, char, None
            if char.isdigit():
                if char in '01234567' and self.look_ahead('01234567', '01234567'):
                    # we have got a 3-digit octal escape
                    char += self.get_char()+self.get_char()
                    return '\\'+char, '\\'+char, unichr(int(char, 8))
                elif char == '0' and self.look_ahead('1234567'):
                    # we have got a 2-digit octal escape
                    char += self.get_char()
                    return '\\'+char, '\\'+char, unichr(int(char, 8))
                elif char == '0':
                    # we have got a zero-byte-escape
                    return '\\0', '\\0', '\0'
                else:  # char in '123456789'!
                    # we have group backreference
                    if self.look_ahead('0123456789'):
                        char += self.get_char()
                    if place != PLACE_REGEXP and place != PLACE_REPL:
                        raise SedException(
                            pos,
                            '\\{esc} is a group backreference outside of a regexp or replacement.',
                            esc=char)
                    char = '\\'+char
                    return char, '(?:'+char+')', None
            if char == 'x':
                hex_num = (self.get_char() + self.get_char())
                char = '\\x' + hex_num
                try:
                    num = int(hex_num, 16)
                    return char, char, unichr(num)
                except ValueError:
                    raise SedException(
                        pos,
                        'Invalid hex code in byte escape {esc}',
                        esc=char)
            elif char == 'u':
                hex_num = (self.get_char()
                           + self.get_char()
                           + self.get_char()
                           + self.get_char())
                char = '\\u' + hex_num
                try:
                    num = int(hex_num, 16)
                    return char, char, unichr(num)
                except ValueError:
                    raise SedException(
                        pos,
                        'Invalid hex code in unicode escape {esc}',
                        esc=char)
            elif char == 'U':
                hex_num = (self.get_char()
                           + self.get_char()
                           + self.get_char()
                           + self.get_char()
                           + self.get_char()
                           + self.get_char()
                           + self.get_char()
                           + self.get_char())
                char = '\\U' + hex_num
                try:
                    num = int(hex_num, 16)
                    return char, char, unichr(num)
                except ValueError:
                    raise SedException(
                        pos,
                        'Invalid hex code in unicode escape {esc}',
                        esc=char)
            elif char == 'N':
                char = self.get_char()
                if char != '{':
                    raise SedException(
                        pos,
                        'Invalid unicode escape \\N{char}. ' +
                        'Expected { but found {char}',
                        char=char)
                char, nme = self.get_unicode_name()
                if char != '}':
                    raise SedException(
                        pos,
                        'Invalid unicode escape \\N{{{esc}. ' +
                        'Missing } behind the character name.',
                        esc=nme)
                nme = '\\N{' + nme + '}'
                return nme, nme, codecs.getdecoder('unicode_escape')(nme)[0]
        if char.isalnum() and place != PLACE_TEXT:
            raise SedException(pos,
                               '\\{char} is not a valid escape in a {plce}.',
                               char=char,
                               plce=PLACE_NAMES[place])
        # keep everything else as it was
        return '\\' + char, '\\' + char, char

    def get_regexp(self, delim, address=True):
        position = self.position
        swap_escapes = not self.sed.regexp_extended and self.sed.sed_compatible
        char = self.get_char()
        if char == delim:
            regexp = SedRegexpEmpty(position, delim, address=address)
        else:
            # we use this to keep track of $ characters
            # in the python pattern since we may need to
            # modify them to achieve sed compatibility,
            # because the dollar sign has context-dependent
            # behavior in sed:
            #  1. $ not at the end of a regular expression
            #     are to be taken literally
            #  2. in a single line substitution $ only
            #     matches the end of the pattern space
            #  3. in a multi line substitution $ matches
            #     the end of the pattern space AND right
            #     before any new-line
            # This is a problem, because in a python regexp
            # $ always behaves like 3.
            # So for 1. we need to replace $ with \\$ and
            # for 2. we need to replace $ with \\Z.
            # Unfortunately, we can only decide what to do
            # for 2. AFTER we parsed the flags behind
            # the regexp and in the case of the s command
            # even later - after parsing the sed-flags
            dollars = []
            pattern = ''
            py_pattern = ''
            pychr = ''
            last_char = ''
            last_pychr = ''
            while char != '\0' and char != delim:
                pychr = char
                processed = False
                if char == '\\':
                    processed = True
                    if swap_escapes and self.look_ahead('(){}|+?'):
                        chr2 = self.get_char()
                        char += chr2
                        pychr = chr2
                    elif self.look_ahead(delim):
                        char = self.get_char()
                        pychr = char
                    else:
                        char, pychr, unesc = self.get_escape(PLACE_REGEXP)
                        # Module re only supports \\u, \\U from Python 3.3 and
                        # \\N from 3.8. So we resolve these escape sequences here,
                        # to allow using them even with earlier Python versions.
                        # Furthermore byte-escape sequences under sed comaptibility
                        # may specify multi-byte characters in the encoding. They
                        # are resolved here as well. And the resolved characters
                        # are processed as if they where specified in the script
                        # themselves. Meaning, that special characters like ^ max
                        # be specified through byte- or unicode-escapes. Just like
                        # with GNU sed.
                        if pychr[:2] in ['\\u', '\\U', '\\N', '\\x']:
                            char = unesc
                            processed = False

                if not processed:
                    # backslashes coming from byte-escapes will stand for themselves
                    pychr = char
                    if char == '\\':
                        char = '\\\\'
                        pychr = char
                    elif char in '(){}|+?':
                        if swap_escapes:
                            pychr = '\\' + pychr
                    elif char == '[':
                        char, pychr = self.get_charset()
                    elif self.sed.sed_compatible:
                        # in sed a ^ not at the beginning of
                        # a regexp must be taken literally
                        if char == '^' and last_pychr not in ['(', '|', '']:
                            pychr = '\\^'
                        elif char == '$':
                            # remember this dollar sign's position in py_pattern
                            dollars.append(len(py_pattern))

                if self.sed.sed_compatible and pychr == '?' \
                   and last_pychr in ['(', '+', '*']:
                    raise SedException(
                        self.position,
                        'Invalid regexp: {last}{char} is not allowed ' +
                        'in sed compatible mode.',
                        char=char,
                        last=last_char)
                pattern += char
                py_pattern += pychr
                last_char = char
                last_pychr = pychr
                char = self.get_char()
            if char != delim:
                raise SedException(
                    self.position,
                    'Invalid regex: expected closing delimiter {delim}',
                    delim=delim)
            regexp = SedRegexp(position, delim, pattern,
                               py_pattern, dollars, address=address)
        if address:
            multi_line = False
            ignore_case = False
            char = self.get_non_space_char_within_continued_lines()
            while char in ['I', 'M']:
                if char == 'M':
                    if multi_line:
                        raise SedException(
                            self.position,
                            'Invalid regex: flag M specified multiple times')
                    regexp.set_multi_line()
                    multi_line = True
                elif char == 'I':
                    if ignore_case:
                        raise SedException(
                            self.position,
                            'Invalid regex: flag I specified multiple times')
                    regexp.set_ignore_case()
                    ignore_case = True
                char = self.get_non_space_char_within_continued_lines()
        return char, regexp

    def get_charset(self):
        # handle []...] and [^]...]
        charset = '['
        char = self.get_char()
        if char == '^':
            charset += char
            char = self.get_char()
        if char == ']':
            charset += char
            char = self.get_char()
        pyset = charset
        while char != ']' and char != '\0':
            if char == '[' and self.look_ahead(':=.'):
                position = self.position
                class_char = self.get_char()
                class_name = {':': 'character class',
                              '=': 'equivalence class',
                              '.': 'collating symbol'}[class_char]
                char2, nme = self.get_name(class_name)
                if char2 != class_char or not self.look_ahead(']'):
                    char = self.get_char()
                    raise SedException(
                        position,
                        '[{clschr}{nme}{char2}{char} in charset' +
                        ' is not a valid {cls} specification',
                        clschr=class_char,
                        nme=nme,
                        char2=char2,
                        char=char,
                        cls=class_name)
                char = self.get_char()
                class_spec = '[' + class_char + nme + class_char + ']'
                charset += class_spec
                pyset += charset
                raise SedException(
                    position,
                    'The {nme} specification {spec} is not supported' +
                    ' by Python regular expressions.',
                    nme=class_name,
                    spec=class_spec)
            elif char == '\\':
                esc, pyesc, _ = self.get_escape(PLACE_CHRSET)
                charset += esc
                pyset += pyesc
            else:
                charset += char
                pyset += char
            char = self.get_char()
        if char != ']':
            raise SedException(self.position,
                               'Invalid regex: charset not closed')
        return charset + char, pyset + char

    def get_replacement(self, delim):
        replacement = Replacement()
        char = self.get_char()
        while char != '\0' and char != delim:
            if char == '\\':
                if self.look_ahead(delim):
                    char = self.get_char()
                    replacement.add_literal('\\' + char, char)
                else:
                    char, pychr, unesc = self.get_escape(PLACE_REPL)
                    if unesc is not None:
                        replacement.add_literal(char, unesc)
                    else:
                        replacement.add_escape(char, pychr)
            elif char == '&' and self.sed.sed_compatible:
                replacement.add_group(char, 0)
            else:
                replacement.add_literal(char, char)
            char = self.get_char()
        if char != delim:
            return None
        return replacement

    def get_address(self):
        from_addr = None
        addr_range = None
        char = self.script_line.skip_over_end_of_cmd()
        position = self.position
        if char == '\0':
            return position, None, None
        if char == '\\' or char == '/':
            if char == '\\':
                char = self.get_char()
            char, regexp = self.get_regexp(char, address=True)
            # make sure we keep sed compatibility
            regexp.process_flags_and_dollars()
            from_addr = AddressRegexp(self.sed, regexp)
        elif char in '0123456789':
            char, num = self.get_number(char)
            if char == '~':
                char, step = self.get_number()
                if step > 0:
                    from_addr = AddressStep(self.sed, num, step)
                elif num == 0:
                    from_addr = AddressZero(self.sed)
                else:
                    from_addr = AddressNum(self.sed, num)
            elif num == 0:
                from_addr = AddressZero(self.sed)
            else:
                from_addr = AddressNum(self.sed, num)
        elif char == '$':
            from_addr = AddressLast(self.sed)
            char = self.get_char()
            self.needs_last_line = True
        else:  # no address found
            return position, AddressRangeNone(), char
        char = self.script_line.skip_space_within_continued_lines()
        if char == ',':
            char = self.script_line.get_non_space_char_within_continued_lines()
            if char == '\0':
                raise SedException(
                    self.position,
                    'Invalid address specification: missing to-address')
            exclude = False
            excl_pos = self.position
            if char == '-':
                exclude = True
                char = self.get_non_space_char_within_continued_lines()
            if char == '\\' or char == '/':
                if char == '\\':
                    char = self.get_char()
                char, regexp = self.get_regexp(char, address=True)
                # make sure we keep sed compatibility
                regexp.process_flags_and_dollars()
                if isinstance(from_addr, AddressZero):
                    addr_range = AddressRangeZeroToRegexp(from_addr,
                                                          regexp,
                                                          exclude)
                else:
                    addr_range = AddressRangeToRegexp(from_addr,
                                                      regexp,
                                                      exclude)
            elif char in '0123456789':
                num_pos = self.position
                char, num = self.get_number(char)
                if num == 0:
                    raise SedException(num_pos, 'Invalid use of zero address')
                addr_range = AddressRangeToNum(from_addr, num, exclude)
            elif char == '~':
                char, multiple = self.get_number()
                if multiple == 0:
                    if exclude:
                        raise SedException(excl_pos,
                                           'Invalid use of exclude flag')
                    addr_range = AddressRangeFake(from_addr)
                else:
                    addr_range = AddressRangeToMultiple(from_addr,
                                                        multiple,
                                                        exclude)
            elif char == '+':
                char, count = self.get_number()
                if count == 0:
                    if exclude:
                        raise SedException(excl_pos,
                                           'Invalid use of exclude flag')
                    addr_range = AddressRangeFake(from_addr)
                else:
                    addr_range = AddressRangeToCount(from_addr, count, exclude)
            elif char == '$':
                addr_range = AddressRangeToLastLine(from_addr, exclude)
                char = self.get_char()
                self.needs_last_line = True
            else:
                raise SedException(self.position,
                                   'Invalid to-address in address range')
        else:  # only an address found - no range
            addr_range = AddressRangeFake(from_addr)
        char = self.script_line.skip_space_within_continued_lines()
        if (isinstance(from_addr, AddressZero) and
            not isinstance(addr_range,
                           AddressRangeZeroToRegexp)):
            raise SedException(position, 'Invalid use of zero address')
        if char == '!':
            char = self.get_non_space_char_within_continued_lines()
            addr_range.set_negate(True)
        return position, addr_range, char

    def reference_to_label(self, label_ref_command):
        label = label_ref_command.label
        if label in self.defined_labels:
            label_ref_command.branch = self.defined_labels[label]
        else:
            ref = self.referenced_labels.get(label, None)
            if ref:
                ref.append(label_ref_command)
            else:
                self.referenced_labels[label] = [label_ref_command]

    def define_label(self, label_def_command):
        label = label_def_command.label
        if label in self.defined_labels:
            raise SedException(
                self.position,
                'Label {lbl} redefined at {redef} (first appeared at {orig})',
                lbl=label,
                redef=label_def_command.position,
                orig=self.defined_labels[label].position)
        self.defined_labels[label] = label_def_command
        references = self.referenced_labels.pop(label, [])
        for cmd in references:
            cmd.branch = label_def_command

    def register_block_start(self, block_start_cmd):
        self.started_blocks.append(block_start_cmd)

    def process_block_end(self, block_end_cmd):
        if len(self.started_blocks) > 0:
            block_start_cmd = self.started_blocks.pop()
            if block_start_cmd.next:
                block_start_cmd.branch = block_start_cmd.next
            else:  # we have got an empty block!
                block_start_cmd.branch = block_end_cmd
            block_start_cmd.next = block_end_cmd
        else:
            raise SedException(block_end_cmd.position,
                               'No matching open block for block end command')


class Sed(object):
    u"""Usage:
    from PythonSed import Sed, SedException
    sed = Sed()
    sed.no_autoprint = True/False
    sed.regexp_extended = True/False
    sed.in_place = None/Backup-Suffix
    sed.separate = True/False
    sed.debug = debug level (0=no debug, 1=debug execution,
                             2=debug compile, 3=trace compile)
    sed.load_script(myscript)             file name or open file or stream
    sed.load_string(mystring)             literal string
    sed.load_scripts(myscripts)           list of file names, files or streams
    lines = sed.apply(myinput)            print lines to stdout
    lines = sed.apply(myinput, None)      do not print lines
    lines = sed.apply(myinput, myoutput)  print lines to myoutput
    myinput and myoutput may be:
    * strings, in that case they are interpreted as file names
    * file-like objects (including streams)
    Note that if myinput or myoutput are file-like objects, they must be closed
    by the caller.
    """

    def __init__(self,
                 encoding=DEFAULT_ENCODING,
                 line_length=70,
                 no_autoprint=False,
                 regexp_extended=False,
                 sed_compatible=True,
                 in_place=None,
                 separate=False,
                 debug=0):
        self.encoding = encoding
        self.line_length = line_length
        self.no_autoprint = no_autoprint
        self.regexp_extended = regexp_extended
        self.sed_compatible = sed_compatible
        self.in_place = in_place
        self.separate = separate
        self.debug = debug
        self.writer = None
        self.reader = None
        self.PS = ''
        self.HS = ''
        self.subst_successful = False
        self.append_buffer = []
        self.script = Script(self)
        self.exit_code = 0

    def normalize_string(self, strng, line_length):
        if strng is None:  # pragma: no cover (debug only)
            yield ''
            return
        byteArray = bytearray(strng, self.writer.current_encoding)
        x = ''
        for c in byteArray:
            if 32 <= c <= 127:
                c = unichr(c)
                if c == '\\':
                    x += c
                x += c
            elif c == ord('\a'):
                x += '\\a'
            elif c == ord('\f'):
                x += '\\f'
            elif c == ord('\n'):
                x += '\\n'
            elif c == ord('\r'):
                x += '\\r'
            elif c == ord('\t'):
                x += '\\t'
            elif c == ord('\v'):
                x += '\\v'
            else:
                o = oct(c)
                if o.startswith('0o'):
                    o = o[2:]
                x += '\\' + ('000'+o)[-3:]
        width = line_length - 1
        while len(x) > width:
            yield (x[:width] + '\\')
            x = x[width:]
        yield (x + '$')

    def write_state(self, title):
        self.stateWriter.writeState(title)

    def load_script(self,
                    filename,
                    encoding=None):
        if encoding is None:
            encoding = self.encoding
        if type(filename) == str or PY2 and type(filename) == unicode:
            self.script.add_file(filename, encoding)
        else:
            self.script.add_object(filename, encoding)

    def load_string(self, string, encoding=None):
        if encoding is None:
            encoding = self.encoding
        if type(string) == list:
            self.load_string_list(string, encoding=encoding)
        else:
            self.script.add_string(string, encoding)

    def load_string_list(self, string_list, encoding=None):
        if type(string_list) != list:
            raise SedException('', 'Input to load_string_list must be a list of strings.')
        if encoding is None:
            encoding = self.encoding
        buffer = StringIO()
        for strg in string_list:
            strg = make_unicode(strg, encoding)
            buffer.write(strg)
            if not strg.endswith('\n'):
                buffer.write('\n')
        self.script.add_string(buffer.getvalue(), encoding)

    def readline(self):
        self.subst_successful = False
        return self.reader.readline()

    def is_last_line(self):
        return self.reader.is_last_line()

    def file_line_no(self):
        return self.reader.line_number

    def printline(self, source, line):
        self.writer.printline(line)
        if self.debug > 0:
            prefix = 'printing (' + source + '): '
            for lne in line.split('\n'):
                DEBUG('{prefix}{lne}', prefix=prefix, lne=lne.replace(' ', '\N{MIDDLE DOT}'))

    def flush_append_buffer(self):
        for line in self.append_buffer:
            self.printline('appnd', line)
        self.append_buffer = []

    def getReader(self,
                  inputs,
                  encoding,
                  writer,
                  separate,
                  needs_last_line):
        if needs_last_line:
            if writer.is_inplace():
                return ReaderBufferedSeparateInputsInplace(inputs, encoding, writer)
            elif separate:
                return ReaderBufferedSeparateInputs(inputs, encoding)
            else:
                return ReaderBufferedOneStream(inputs, encoding)
        elif writer.is_inplace():
            return ReaderUnbufferedSeparateInputsInplace(inputs, encoding, writer)
        elif separate:
            return ReaderUnbufferedSeparateInputs(inputs, encoding)
        else:
            return ReaderUnbufferedOneStream(inputs, encoding)

    def apply(self, inputs, output=sys.stdout):
        try:
            DEBUG_ENCODING = self.encoding  # in case it was changed since object instantiation
            self.writer = Writer(output,
                                 self.encoding,
                                 self.in_place,
                                 self.debug)
            first_cmd = self.script.get_first_command()
            if first_cmd is None:
                raise SedException('', 'Empty script specified.')
            if self.debug > 0:
                DEBUG('Configuration:')
                DEBUG('  debug={dbg}', dbg=self.debug)
                DEBUG('  encoding={enc}', enc=self.encoding)
                DEBUG('  line_length={len}', len=self.line_length)
                DEBUG('  no_autoprint={np}', np=self.no_autoprint)
                DEBUG('  regexp_extended={ext}', ext=self.regexp_extended)
                DEBUG('  sed_compatible={comp}', comp=self.sed_compatible)
                DEBUG('  in_place={inp}', inp=('<off>' if self.in_place is None
                                               else u"'"+self.in_place+u"'"))
                DEBUG('  separate={sep}', sep=self.separate)
                DEBUG('')
                DEBUG('{scr}', scr=self.script)
                self.stateWriter = StateWriter(self)
            self.reader = self.getReader(
                            inputs,
                            self.encoding,
                            self.writer,
                            self.separate,
                            self.script.needs_last_line)
            self.exit_code = 0
            self.HS = ''
            self.subst_successful = False
            self.append_buffer = []
            SedRegexp.last_regexp = None
            self.PS = self.readline()

            while self.PS is not None:
                matched, command = False, first_cmd
                if self.debug > 0:
                    DEBUG('############### new cycle '.ljust(self.line_length, '#'))
                    DEBUG('Auto Print: {ap}', ap='Off' if self.no_autoprint else 'On')
                    DEBUG('Input File: {fle}[{idx}]',
                          fle=self.reader.source_file_name,
                          idx=self.reader.line_number)
                    DEBUG('Output To : {fle}', fle=self.writer.current_filename)
                    self.write_state('current')
                last_relevant_command = ' '
                while command:
                    prev_command = command
                    matched, command = command.apply_func(self)
                    if matched:
                        last_relevant_command = prev_command.function

                if self.debug > 0:
                    DEBUG('############### cycle end '.ljust(self.line_length, '#'))
                    DEBUG('Auto Print: {ap}', ap='Off' if self.no_autoprint else 'On')
                    DEBUG('Input File: {fle}[{idx}]',
                          fle=self.reader.source_file_name,
                          idx=self.reader.line_number)
                    DEBUG('Output To : {fle}', fle=self.writer.current_filename)
                    DEBUG('Last Command: {cmd}', cmd=last_relevant_command)
                    DEBUG('Pattern space is None: {flag}', flag=(self.PS is None))
                if not (self.no_autoprint
                        or last_relevant_command in 'DQ'
                        or self.PS is None):
                    self.printline('autop', self.PS)
                self.flush_append_buffer()
                if last_relevant_command in 'qQ':
                    self.exit_code = prev_command.exit_code or 0
                    break
                if last_relevant_command != 'D':
                    self.PS = self.readline()
        except SedException as e:
            sys.stderr.write(e.message+'\n')
            self.exit_code = 1
        except:  # noqa: E722  # pragma: no cover
            traceback.print_exception(*sys.exc_info(), file=sys.stderr)
            self.exit_code = 1
        finally:
            if self.reader:
                self.reader.close()
            return self.writer.finish()


class StateWriter(object):

    def __init__(self, sed):
        self.sed = sed
        self.last_PS = []
        self.last_HS = []
        self.last_append_buffer = []
        self.last_subst_successful = None

    def _create_printable(self, lines_list, width):
        result = []
        for multi_lines in lines_list:
            if multi_lines is not None:
                splitted = list(lne + '\n' for lne in multi_lines.split('\n'))
                # remove newline from last line
                splitted[-1] = splitted[-1][:-1]
                for line in splitted:
                    for normalized in self.sed.normalize_string(line, width):
                        result.append('|{lne:<{width}s}|'.format(
                            lne=normalized.replace(' ', '\N{MIDDLE DOT}'),
                            width=width))
        if len(result) == 0:
            result.append('|{lne:<{width}s}|'.format(lne='', width=width))
        return result

    def _write_list(self, title, last_list, new_list):
        DEBUG('{tit}:', tit=title)
        for i in range(len(new_list)):
            flag = '  '
            if i >= len(last_list) or last_list[i] != new_list[i]:
                flag = '* '
            DEBUG('{flg}{lne}', flg=flag, lne=new_list[i])

    def writeState(self, title):
        width = self.sed.line_length - 4
        DEBUG('{tit}', tit=('--------------- ' + title + ' ').ljust(self.sed.line_length, '-'))
        new = self._create_printable([self.sed.PS], width)
        self._write_list('Pattern Space', self.last_PS, new)
        self.last_PS = new

        new = self._create_printable([self.sed.HS], width)
        self._write_list('Hold Space', self.last_HS, new)
        self.last_HS = new

        new = self._create_printable(self.sed.append_buffer, width)
        self._write_list('Append Buffer', self.last_append_buffer, new)
        self.last_append_buffer = new

        new = ('' if self.last_subst_successful == self.sed.subst_successful
               else '*')
        DEBUG('{flg}Substitution successful: {sub}', flg=new, sub=self.sed.subst_successful)
        self.last_subst_successful = self.sed.subst_successful


class Writer (object):

    def __init__(self, output, encoding, in_place, debug=0):
        self.default_encoding = encoding
        self.current_encoding = encoding
        self.in_place = make_unicode(in_place, sys.getfilesystemencoding())
        self.debug = debug
        self.output_lines = []
        self.open_files = {}
        self.current_filename = None
        self.current_output = None
        self.current_output_opened = False
        self.inplace_filenames = {}
        if in_place is None:
            if type(output) == str or PY2 and type(output) == unicode:
                self.current_filename = make_unicode(output, sys.getfilesystemencoding())
                try:
                    self.current_output = open(self.current_filename, 'wt', encoding=encoding)
                    self.current_output_opened = True
                except Exception as e:
                    raise SedException(
                        '', 'Can not open output file {file}: {err}',
                        file=self.current_filename,
                        err=make_unicode(str(e), encoding))
            elif output is not None:
                self.current_output = output  # we assume it is an output stream

    def is_inplace(self):
        return self.in_place is not None

    def printline(self, line):
        if self.current_output:
            # self.current_output if not None, will always point to a stream
            # that expects unicode to be written to. That means, if a stream
            # is passed in as output to sed.apply, THAT stream must accept
            # unicode data as well.
            try:
                self.current_output.write(line+'\n')
            except:
               # bail out immediately if we have any problem with encodings here
               sys.stderr.write(traceback.format_exc())
               sys.exit(1)
        self.output_lines.extend(lne+'\n' for lne in line.split('\n'))

    def add_write_file(self, filename):
        if self.open_files.get(filename) is None:
            if filename in ['/dev/stdout', '-']:
                writer = sys.stdout
                self.open_files['/dev/stdout'] = writer
                self.open_files['-'] = writer
            elif filename == '/dev/stderr':
                self.open_files['/dev/stderr'] = sys.stderr
            else:
                self.open_files[filename] = open(filename, 'wt', encoding=self.default_encoding)

    def write_to_file(self, filename, line):
        open_file = self.open_files.get(filename)
        if open_file is None:  # pragma: no cover (should never happen)
            raise SedException('', 'File {file} not opened for writing.', file=filename)
        if not line.endswith('\n'):
            line += '\n'
        if self.debug > 0:  # pragma: no cover (debug only)
            DEBUG('writing to {fle}: {txt}',
                  fle=filename,
                  txt=line.replace(' ', '\N{MIDDLE DOT}'))
        open_file.write(line)

    def open_inplace(self, filename):
        self.current_filename = os.path.abspath(filename)
        directory = os.path.dirname(self.current_filename)
        prefix = os.path.basename(self.current_filename)+'.'
        self.current_output = NamedTemporaryFile(dir=directory,
                                                 prefix=prefix,
                                                 mode='wt',
                                                 delete=False)
        self.current_output_opened = True

    def close_inplace(self):
        if self.current_output:
            self.current_output.close()
            self.current_output_opened = False
            if len(self.in_place) == 0:
                bkup = NamedTemporaryFile(
                         dir=os.path.dirname(self.current_filename),
                         prefix=os.path.basename(self.current_filename) + '.',
                         delete=False)
                bkup.close()
                bkup = bkup.name
            elif '*' in self.in_place:
                bkup = self.in_place.replace(
                    '*', os.path.basename(self.current_filename))
                if '/' not in bkup:
                    bkup = os.path.join(os.path.dirname(self.current_filename),
                                        bkup)
            else:
                bkup = self.current_filename + self.in_place
            os.rename(self.current_filename, bkup)
            os.rename(self.current_output.name, self.current_filename)
            if len(self.in_place) == 0:
                os.remove(bkup)

    def finish(self):
        if self.current_output_opened:
            if self.in_place is not None:
                try:
                    self.close_inplace()
                except IOError:  # pragma: no cover (should never happen)
                    pass
            else:
                try:
                    self.current_output.close()
                except IOError:  # pragma: no cover (happens only with real IO errors)
                    pass
        for (filename, open_file) in self.open_files.items():
            try:
                if filename not in ['/dev/stdout', '/dev/stderr', '-']:
                    open_file.close()
            except IOError:  # pragma: no cover (happens only with real IO errors)
                pass
        self.open_files.clear()
        return self.output_lines


# The following classes provide the stream input readers for the various combinations
# of the ways the input must be processed. The Sed.getReader(...) method selects the
# right class based on the options --separate and --inplace and if any regexp uses $
# and needs to know if a certain line is the last line of an input stream.
# Using different classes for these contstrains allows to read the input without
# constantly having to re-check the options.

class ReaderUnbufferedOneStream(object):
    """ This reader class is used to process all input files/streams as one big
        stream of input lines. There is also no need - or indication for - knowing
        when the last line of input is processed.
    """

    def __init__(self, inputs, encoding):
        if inputs is None:
            self.inputs = [sys.stdin]
        else:
            if type(inputs) != list:
                self.inputs = [inputs]
            else:
                self.inputs = list(inputs)  # create copy of incoming list
            if len(self.inputs) == 0 or \
               len(self.inputs) == 1 \
               and not self.inputs[0]:  # empty or None
                self.inputs = [sys.stdin]

        self.default_encoding = encoding
        self.current_input_encoding = encoding
        self.line = ''
        self.line_number = 0
        self.source_file_name = None
        self.open_index = 0
        self.open_next()
        self.open_files = {}

    def check_inplace_inputs(self, inputs):
        files = inputs
        if type(inputs) != list:
            files = [inputs]
        if len(files) == 0:
            raise SedException(
                '', 'Can not use stdin as input for inplace-editing.')
        for fle in files:
            if type(fle) == tuple:  # do we have an (encoding,input) tuple
                fle = fle[1]
            if fle in [None, '', '-', '/dev/stdin']:
                raise SedException(
                    '', 'Can not use stdin as input for inplace-editing.')
            elif not (type(fle) == str or PY2 and type(fle) == unicode):
                raise SedException(
                    '', 'Can not use streams, files or literals as input for inplace-editing.')

    def open_next(self):
        if len(self.inputs) == 0:
            self.input_stream = None
            self.input_stream_opened = False
            return
        self.open_index += 1

        next_input = self.inputs.pop(0)
        if type(next_input) == tuple:
            self.current_input_encoding = next_input[0]
            next_input = next_input[1]
        else:
            self.current_input_encoding = self.default_encoding

        if type(next_input) == list:
            result = ''
            for lne in next_input:
                lne = make_unicode(lne, self.current_input_encoding)
                result += lne
                if not lne.endswith('\n'):
                    result += '\n'
            self.input_stream = StringIO(result)
            self.source_file_name = '<literal[{}]>'.format(self.open_index)
            self.input_stream_opened = True
        elif type(next_input) == str or PY2 and type(next_input) == unicode:
            try:
                self.source_file_name = make_unicode(next_input, sys.getfilesystemencoding())
            except UnicodeDecodeError as e:
                raise SedException(
                    '', 'Unable to convert file name {fle} to unicode using encoding {enc}',
                    fle=codecs.getdecoder('latin1', 'replace')(next_input)[0],
                    enc=sys.getfilesystemencoding())

            if self.source_file_name in ['-', '/dev/stdin']:
                self.input_stream = sys.stdin
                self.source_file_name = '<stdin[{}]>'.format(self.open_index)
                self.input_stream_opened = False
            else:
                self.input_stream_opened = True
                try:
                    self.input_stream = open(self.source_file_name, 'rt',
                                             encoding=self.current_input_encoding)
                except IOError as e:
                    raise SedException(
                        '', 'Unable to open input file {file}: {err}',
                        file=self.source_file_name,
                        err=make_unicode(str(e), self.default_encoding))
        else:
            self.input_stream = next_input
            self.source_file_name = '<stream[{}]>'.format(self.open_index)
            self.input_stream_opened = False

    def readline(self):
        if self.input_stream is None:
            return None
        self.line = self.next_line()
        while self.line == '':
            if self.input_stream_opened:
                self.input_stream.close()
                self.input_stream_opened = False
            self.open_next()
            if self.input_stream is None:
                return None
            self.line = self.next_line()
        self.line_number += 1
        if self.line.endswith('\n'):
            self.line = self.line[:-1]
        return self.line

    def next_line(self):
        return make_unicode(self.input_stream.readline(), self.current_input_encoding)

    def readline_from_file(self, filename):
        if filename not in self.open_files:
            open_file = None
            try:
                if filename in ['/dev/stdin', '-']:
                    open_file = sys.stdin
                    self.open_files['/dev/stdin'] = open_file
                    self.open_files['-'] = open_file
                else:
                    open_file = open(filename, 'rt', encoding=self.default_encoding)
                    self.open_files[filename] = open_file
            except IOError:
                self.open_files[filename] = None
                return ''

        open_file = self.open_files.get(filename)
        if open_file is None:
            return ''
        try:
            line = make_unicode(open_file.readline(), self.default_encoding)
        except IOError:  # pragma: no cover (not testable)
            line = ''
        if len(line) == 0:
            if filename not in ['-', '/dev/stdin']:
                try:
                    open_file.close()
                except Exception:  # pragma: no cover (not testable)
                    pass
            self.open_files[filename] = None
        return line

    def close(self):
        if self.input_stream_opened:
            try:
                self.input_stream.close()
            except IOError:  # pragma: no cover (not testable)
                pass
        for (filename, open_file) in self.open_files.items():
            if filename not in ['-', '/dev/stdin'] and open_file is not None:
                try:
                    open_file.close()
                except IOError:  # pragma: no cover (not testable)
                    pass


class ReaderUnbufferedSeparateInputs(ReaderUnbufferedOneStream):
    """ This reader class is used, if the input streams/files are to be processed
        individually - meaning that the line-number for the lines read will restart
        with 0 for each new input stream/file.
        There is no need - or indication for - when the last line of input of a stream
        or file is being processed.
    """
    def open_next(self):
        self.line_number = 0
        ReaderUnbufferedOneStream.open_next(self)


class ReaderUnbufferedSeparateInputsInplace(ReaderUnbufferedSeparateInputs):
    """ This reader class is used, if inplace-editing is requested. That restricts
        the input to be a list of file names and streams (especially stdin) can thus
        not be processed.
        There is no need - or indication for - when the last line of an input file
        is being processed.
        A callback to the writer instance is used to signal, that the output is to be
        routed to a new temporary file and the current output file is to be renamed
        to replace the current input file, if an input file reaches EOF.
    """

    def __init__(self, inputs, encoding, writer):
        self.check_inplace_inputs(inputs)
        self.writer = writer
        ReaderUnbufferedSeparateInputs.__init__(self, inputs, encoding)

    def open_next(self):
        self.writer.close_inplace()
        ReaderUnbufferedSeparateInputs.open_next(self)
        if self.input_stream is not None:
            self.writer.open_inplace(
                self.source_file_name)
        return self.input_stream


class ReaderBufferedOneStream(ReaderUnbufferedOneStream):
    """ This reader class is just like ReaderUnbufferedOneStream except
        that the information about the input being on the last line of the
        total input is available to the address range object instances.
    """

    # used if last line address ($) required
    # buffer one line to be used from input stream
    def open_next(self):
        ReaderUnbufferedOneStream.open_next(self)
        if self.input_stream:
            self.nextline = make_unicode(self.input_stream.readline(),
                                         self.current_input_encoding)

    def next_line(self):
        if self.nextline != '':
            line = self.nextline
            self.nextline = make_unicode(self.input_stream.readline(),
                                         self.current_input_encoding)
            return line
        else:
            return ''

    def is_last_line(self):
        return self.nextline == '' and len(self.inputs) == 0


class ReaderBufferedSeparateInputs(ReaderBufferedOneStream):
    """ This reader class is just like ReaderUnbufferedSeparateInputs except
        that the information about the input being on the last line of the
        current input stream/file is available to the address range object instances.
    """

    def open_next(self):
        self.line_number = 0
        ReaderBufferedOneStream.open_next(self)

    def is_last_line(self):
        return self.nextline == ''


class ReaderBufferedSeparateInputsInplace(ReaderBufferedSeparateInputs):
    """ This reader class is just like ReaderUnbufferedSeparateInputsInplace except
        that the information about the input being on the last line of the current
        input file is available to the address range object instances.
    """

    def __init__(self, inputs, encoding, writer):
        self.check_inplace_inputs(inputs)
        self.writer = writer
        ReaderBufferedSeparateInputs.__init__(self, inputs, encoding)

    def open_next(self):
        self.writer.close_inplace()
        ReaderBufferedSeparateInputs.open_next(self)
        if self.input_stream is not None:
            self.writer.open_inplace(self.source_file_name)
        return self.input_stream


# The following classes implement the various sed commands. Each command
# found in the script is translated into an instance of one of those classes
# and the Sed.apply function that justs 'plays' down the list of these command
# instances.


class Command(object):

    def __init__(self, script, addr_range, function):
        self.position = script.position
        self.num = script.command_index()
        if (function in [':', '}'] and not isinstance(addr_range, AddressRangeNone)):
            raise SedException(self.position,
                               'No address can be specified for command {cmd}',
                               cmd=function)
        elif (function == 'q'
              and not (isinstance(addr_range, AddressRangeFake)
                       or isinstance(addr_range, AddressRangeNone))):
            raise SedException(
                self.position,
                'No address range can be specified for command {cmd}',
                cmd=function)
        self.function = function
        self.addr_range = addr_range
        self.next = None
        self.branch = None
        self.parse_arguments(script)

    @staticmethod
    def factory(script, addr_range, function):
        if function in COMMANDS:
            return COMMANDS[function](script, addr_range, function)
        else:
            raise SedException(script.position,
                               'Unknown command {cmd}',
                               cmd=function)

    def __str__(self):
        return self.toString(20)

    def toString(self, addr_width=''):
        return '|{num:03d}|{nxt:3s}|{brnch:3s}| {addr:<{wid}s} {cmd:1s}{args}'\
                .format(num=self.num,
                        nxt=(('%03d' % self.next.num)
                             if self.next
                             else ' - '),
                        brnch=(('%03d' % self.branch.num)
                               if self.branch
                               else '   '),
                        addr=str(self.addr_range),
                        wid=addr_width,
                        cmd=self.function,
                        args=self.str_arguments())

    def str_arguments(self):  # pragma: no cover (only debug code)
        return ''

    def parse_arguments(self, script):
        _ = script.get_char()
        if not script.script_line.is_end_of_cmd():
            raise SedException(self.position,
                               'Extra characters after command {cmd}',
                               cmd=self.function)

    def apply_func(self, sed):
        if self.addr_range.is_active():
            if sed.debug > 0:
                DEBUG(' =============== executing '.ljust(sed.line_length, '='))
                DEBUG('{cmd}', cmd=self.toString())
                cmd = self.apply(sed)
                sed.write_state('after')
                return True, cmd
            else:
                return True, self.apply(sed)
        elif sed.debug > 0:
            DEBUG(' =============== skipping '.ljust(sed.line_length, '='))
            DEBUG('{cmd}', cmd=self.toString())
            sed.write_state('current')
        return False, self.next


class Command_block(Command):

    def __init__(self, script, addr_range, function):
        super(Command_block, self).__init__(script, addr_range, function)
        script.register_block_start(self)

    def apply(self, sed):  # @UnusedVariable
        # self.next is the first instruction after block
        # self.branch is the first instruction within block
        return self.branch

    def parse_arguments(self, script):
        _ = script.get_non_space_char_within_continued_lines()
        # do not check for command end, since it is implicit


class Command_block_end(Command):

    def __init__(self, script, addr_range, function):
        super(Command_block_end, self).__init__(script, addr_range, function)
        script.process_block_end(self)

    def apply(self, sed):  # @UnusedVariable
        return self.next


class _Command_with_label(Command):

    def parse_arguments(self, script):
        _, self.label = script.get_name('label',
                                        alpha_only=False,
                                        skip_space=True)
        if not script.script_line.is_end_of_cmd():
            raise SedException(
                self.position,
                'Command {cmd} can not have any arguments after label',
                cmd=self.function)

    def str_arguments(self):  # pragma: no cover (only debug code)
        return ' ' + self.label


class Command_label(_Command_with_label):

    def __init__(self, script, addr_range, function):
        super(Command_label, self).__init__(script, addr_range, function)
        if self.label is None or len(self.label) == 0:
            raise SedException(self.position, 'Missing label for command :')
        script.define_label(self)

    def apply(self, sed):  # @UnusedVariable
        return self.next


class Command_a(Command):

    def parse_arguments(self, script):
        self.text = script.get_to_line_end()

    def apply(self, sed):
        sed.append_buffer.append(self.text)
        return self.next

    def str_arguments(self):  # pragma: no cover (only debug code)
        return ' ' + self.text


class Command_b(_Command_with_label):

    def __init__(self, script, addr_range, function):
        super(Command_b, self).__init__(script, addr_range, function)
        if self.label:
            script.reference_to_label(self)

    def apply(self, sed):  # @UnusedVariable
        # if label was omitted, self.branch is None and will finish the cycle
        if self.branch:
            return self.branch.next
        else:
            return None


class Command_c(Command_a):

    def apply(self, sed):
        if self.addr_range.first_line:
            sed.printline('cmd c', self.text)
        sed.PS = None
        return None


class Command_d(Command):

    def apply(self, sed):
        sed.PS = None
        return None


class Command_D(Command):

    def apply(self, sed):
        if '\n' in sed.PS:
            sed.PS = sed.PS[sed.PS.index('\n') + 1:]
        else:
            sed.PS = sed.readline()
        return None


class Command_equal(Command):

    def apply(self, sed):
        sed.printline('cmd =', str(sed.reader.line_number))
        return self.next


class Command_F(Command):

    def apply(self, sed):
        sed.printline('cmd F', sed.reader.source_file_name)
        return self.next


class Command_g(Command):

    def apply(self, sed):
        sed.PS = sed.HS
        return self.next


class Command_G(Command):

    def apply(self, sed):
        sed.PS += '\n' + sed.HS
        return self.next


class Command_h(Command):

    def apply(self, sed):
        sed.HS = sed.PS
        return self.next


class Command_H(Command):

    def apply(self, sed):
        sed.HS += '\n' + sed.PS
        return self.next


class Command_i(Command_a):

    def apply(self, sed):
        sed.printline('cmd i', self.text)
        return self.next


class Command_l(Command):

    def parse_arguments(self, script):
        char = script.get_non_space_char_within_continued_lines()
        if char.isdigit():
            _, self.line_length = script.get_number(char)
        else:
            self.line_length = None
        if not script.script_line.is_end_of_cmd():
            raise SedException(
                script.position,
                'Only an integer number can follow command l as parameter')

    def apply(self, sed):
        if self.line_length:
            line_length = self.line_length
        else:
            line_length = sed.line_length
        for lne in sed.normalize_string(sed.PS, line_length):
            sed.printline('cmd l', lne)
        return self.next

    def str_arguments(self):  # pragma: no cover (only debug code)
        return ' ' + str(self.line_length) if self.line_length else ''


class Command_n(Command):

    def apply(self, sed):
        if not sed.no_autoprint:
            sed.printline('cmd n', sed.PS)
        sed.PS = sed.readline()
        if sed.PS is None:
            return None
        else:
            return self.next


class Command_N(Command):

    def apply(self, sed):
        newline = sed.readline()
        if newline is None:
            return None
        else:
            sed.PS = sed.PS + '\n' + newline
            return self.next


class Command_p(Command):

    def apply(self, sed):
        sed.printline('cmd p', sed.PS)
        return self.next


class Command_P(Command):

    def apply(self, sed):
        n = sed.PS.find('\n')
        if n < 0:
            sed.printline('cmd P', sed.PS)
        else:
            sed.printline('cmd P', sed.PS[:n])
        return self.next


class Command_q(Command):

    def parse_arguments(self, script):
        char = script.get_non_space_char_within_continued_lines()
        if char.isdigit():
            _, self.exit_code = script.get_number(char)
        else:
            self.exit_code = None
        if not script.script_line.is_end_of_cmd():
            raise SedException(
                script.position,
                'Only an integer number can follow command {cmd} as parameter'
                .format(self.function))

    def apply(self, sed):  # @UnusedVariable
        # handled in sed.apply
        return None

    def str_arguments(self):  # pragma: no cover (only debug code)
        return ' ' + str(self.exit_code) if self.exit_code else ''


class Command_Q(Command_q):

    def apply(self, sed):  # @UnusedVariable
        # handled in sed.apply
        return None


class Command_r(Command):

    def parse_arguments(self, script):
        self.filename = script.get_to_line_end()
        if not self.filename:
            raise SedException(self.position,
                               'Missing file name for command {cmd}',
                               cmd=self.function)
        self.filename = self.filename

    def apply(self, sed):
        # https://groups.yahoo.com/neo/groups/sed-users/conversations/topics/9096
        try:
            with open(self.filename, 'rt', encoding=sed.encoding) as f:
                for line in f:
                    sed.append_buffer.append(
                        line[:-1] if line.endswith('\n') else line)
        except IOError:
            # if filename cannot be read, it is treated as if it were an empty
            # file, without any error indication. (GNU sed manual page)
            pass
        return self.next

    def str_arguments(self):  # pragma: no cover (only debug code)
        return ' ' + self.filename


class Command_R(Command_r):

    def apply(self, sed):
        line = sed.reader.readline_from_file(self.filename)
        if line:
            sed.append_buffer.append(
                line[:-1] if line.endswith('\n') else line)
        return self.next


class Command_s(Command):

    def parse_arguments(self, script):
        self.count = None
        self.printit = False
        self.ignore_case = False
        self.multiline = False
        self.globally = False
        self.filename = None
        self.delim = script.get_char()
        if self.delim == '\n':
            script.script_line.continue_on_next_line()
        char, self.regexp = script.get_regexp(self.delim, address=False)
        if char != self.delim:
            raise SedException(
                script.position,
                'Missing delimiter ({de}) after regexp parameter in command s',
                de=self.delim)
        if self.delim == '\n':
            script.script_line.continue_on_next_line()
        self.repl = script.get_replacement(self.delim)
        if self.repl is None:
            raise SedException(
                script.position,
                'Missing delimiter ({delim}) after replacement in command s',
                delim=self.delim)
        if self.delim == '\n':
            script.script_line.continue_on_next_line()
        char = script.get_non_space_char_within_continued_lines()
        while char not in ';#}\0':
            if char == 'w':
                self.filename = script.get_to_line_end()
                char = '\0'
                if not self.filename:
                    raise SedException(
                        script.position,
                        'Missing file name for command s option w')
                try:
                    script.sed.writer.add_write_file(self.filename)
                except IOError as e:
                    raise SedException(
                        script.position,
                        'Unable to open file {file} for output from ' +
                        'command s with option w: {err}',
                        file=self.filename,
                        err=make_unicode(str(e), script.sed.encoding))
            elif char == 'p':
                if self.printit:
                    raise SedException(
                        script.position,
                        'Flag p specified twice for command s')
                self.printit = True
                char = script.get_non_space_char_within_continued_lines()
            elif char == 'i' or char == 'I':
                if self.ignore_case:
                    raise SedException(script.position,
                                       'Flag i specified twice for command s')
                self.ignore_case = True
                self.regexp.set_ignore_case()
                char = script.get_non_space_char_within_continued_lines()
            elif char == 'm' or char == 'M':
                if self.multiline:
                    raise SedException(script.position,
                                       'Flag m specified twice for command s')
                self.multiline = True
                self.regexp.set_multi_line()
                char = script.get_non_space_char_within_continued_lines()
            elif char == 'g':
                if self.globally:
                    raise SedException(script.position,
                                       'Flag g specified twice for command s')
                self.globally = True
                char = script.get_non_space_char_within_continued_lines()
            elif char in '0123456789':
                if self.count:
                    raise SedException(script.position,
                                       'Count specified twice for command s')
                self.count = 0
                while char in '0123456789':
                    self.count *= 10
                    self.count += int(char)
                    char = script.get_char()
                char = script.skip_space_within_continued_lines()
            else:
                raise SedException(script.position,
                                   'Invalid flag {flag} for command s',
                                   flag=char)
        if self.count is None:
            self.count = 1
        # make sure we keep sed compatibility
        self.regexp.process_flags_and_dollars()

    def str_arguments(self):  # pragma: no cover (only debug code)
        flags = 'g' if self.globally else ''
        if self.count and self.count > 1:
            flags += str(self.count)
        if self.printit:
            flags += 'p'
        if self.ignore_case:
            flags += 'i'
        if self.multiline:
            flags += 'm'
        if self.filename:
            flags += 'w ' + self.filename
        return '{regex}{repl}{delim}{flags}'.format(
            delim=self.delim,
            regex=self.regexp.toString(),
            repl=self.repl.string,
            flags=flags)

    def apply(self, sed):
        # pattern, repl, count, printit, inplace, write, filename = self.args
        # managing ampersand is done when converting to python format
        success, sed.PS = self.regexp.subn(
            self.repl, sed.PS, self.globally, self.count, sed.sed_compatible)
        sed.subst_successful = sed.subst_successful or success
        if success:
            if self.printit:
                sed.printline('cmd s', sed.PS)
            if self.filename:
                sed.writer.write_to_file(self.filename, sed.PS)
        return self.next


class Command_t(Command_b):

    def apply(self, sed):
        # if label was omitted, self.branch is None and will end the cycle
        if sed.subst_successful:
            sed.subst_successful = False
            if self.branch:
                return self.branch.next
            else:
                return None
        else:
            return self.next


class Command_T(Command_b):

    def apply(self, sed):
        # if label was omitted, self.branch is None and will end the cycle
        if sed.subst_successful:
            sed.subst_successful = False
            return self.next
        elif self.branch:
            return self.branch.next
        else:
            return None


class Command_v(Command):

    def apply(self, sed):  # @UnusedVariable
        return self.next

    def parse_arguments(self, script):
        _, self.version = script.get_name(
            'version', alpha_only=False, skip_space=True)
        if not self.version:
            self.version = '4.0'
        match = re.match('^([0-9]+)(?:\\.([0-9]+)(?:\\.([0-9]+))?)?$',
                         self.version)
        if match:
            version = '%03d' % (int(match.group(1)))
            release = '%03d' % (int(match.group(2)) if match.group(2) else 0)
            fixlevel = '%03d' % (int(match.group(3)) if match.group(3) else 0)
            if version + release + fixlevel > '004008000':
                raise SedException(
                    self.position,
                    'Requested version {version} is above provided ' +
                    'version 4.8.0',
                    version=self.version)
        else:
            raise SedException(
                self.position,
                'Invalid version specification {version}. ' +
                'Use a number like 4.8.0',
                version=self.version)

    def str_arguments(self):  # pragma: no cover (only debug code)
        return ' ' + self.version


class Command_w(Command_r):

    def apply(self, sed):
        sed.writer.write_to_file(self.filename, sed.PS)
        return self.next

    def parse_arguments(self, script):
        super(Command_w, self).parse_arguments(script)
        try:
            script.sed.writer.add_write_file(self.filename)
        except IOError as e:
            raise SedException(
                self.position,
                'Unable to open file {f} for output for command {c}: {e}',
                f=self.filename,
                c=self.function,
                e=make_unicode(str(e), script.sed.encoding))


class Command_W(Command_w):

    def apply(self, sed):
        sed.writer.write_to_file(self.filename, sed.PS.split('\n', 1)[0])
        return self.next


class Command_x(Command):

    def apply(self, sed):
        sed.PS, sed.HS = sed.HS, sed.PS
        return self.next


class Command_y(Command):

    def __init__(self, script, addr_range, function):
        super(Command_y, self).__init__(script, addr_range, function)

    def parse_arguments(self, script):
        self.delim = script.get_char()
        if self.delim == '\n':
            script.script_line.continue_on_next_line()
        char, self.left_strg, self.left = script.get_char_list(self.delim)
        if char != self.delim:
            raise SedException(
                script.position,
                'Missing delimiter {delim} for left parameter to command y',
                delim=self.delim)
        if not self.left:
            raise SedException(self.position,
                               'Missing left parameter to command y')
        if self.delim == '\n':
            script.script_line.continue_on_next_line()
        char, self.right_strg, self.right = script.get_char_list(self.delim)
        if char != self.delim:
            raise SedException(
                script.position,
                'Missing delimiter {delim} for right parameter to command y',
                delim=self.delim)
        if not self.right:
            raise SedException(self.position,
                               'Missing right parameter to command y')
        char = script.get_char()
        if not script.script_line.is_end_of_cmd():
            raise SedException(script.position,
                               'Invalid extra characters after command y')

        if len(self.left) != len(self.right):
            raise SedException(self.position,
                               'Left and right arguments to command y must be of equal length.')
        self.translate_table = dict(zip((ord(c) for c in self.left), self.right))

    def str_arguments(self):  # pragma: no cover (only debug code)
        # source_chars, dest_chars = self.args
        return '{delim}{left}{delim}{right}{delim}'.format(
                   delim=self.delim,
                   left=self.left_strg,
                   right=self.right_strg)

    def apply(self, sed):
        sed.PS = sed.PS.translate(self.translate_table)
        return self.next


class Command_z(Command):

    def apply(self, sed):
        sed.PS = ''
        return self.next


COMMANDS = {'{': Command_block,
            '}': Command_block_end,
            ':': Command_label,
            'a': Command_a,
            'b': Command_b,
            'c': Command_c,
            'd': Command_d,
            'D': Command_D,
            '=': Command_equal,
            'F': Command_F,
            'g': Command_g,
            'G': Command_G,
            'h': Command_h,
            'H': Command_H,
            'i': Command_i,
            'l': Command_l,
            'n': Command_n,
            'N': Command_N,
            'p': Command_p,
            'P': Command_P,
            'q': Command_q,
            'Q': Command_Q,
            'r': Command_r,
            'R': Command_R,
            's': Command_s,
            't': Command_t,
            'T': Command_T,
            'w': Command_w,
            'v': Command_v,
            'W': Command_W,
            'x': Command_x,
            'y': Command_y,
            'z': Command_z}


class Replacement(object):
    """ This class is used by the s command to represent the desired replacement
        if a match is found in the pattern space. The replacement part of the s command
        is compiled into an instance of this class, that is then later used to construct
        the replacement string for a given match in the pattern space.

        A Replacement consists of a list of 'cases'. Each case has a pair of case setter
        functions associated with it, that defines, what case-changes have to be done
        1. to the whole case and
        2. to the case's first character

        The case setting is stored as function references to avoid if-elif-cascades during
        processing of the s command and construction of the replacement string for a match.

        Each case in turn contains a list of parts which can be either a group back-reference
        or a literal string.

        To form a replacement string all cases are processed and concatinated.
        A case is processed by concatinating all it's parts and then applying the
        case-settings defined for the case by calling the stored case setter functions.
    """

    CASE_ASIS = '\\E'
    CASE_LOWER = '\\L'
    CASE_UPPER = '\\U'
    CASE_FLIP_NONE = '\\E'
    CASE_FLIP_LOWER = '\\l'
    CASE_FLIP_UPPER = '\\u'

    def __init__(self):
        self.string = ''
        self.cases = [CaseSetter(self.CASE_ASIS, self.CASE_FLIP_NONE)]

    def __str__(self):  # pragma: no cover (only for debugging)
        return self.string

    def __repr__(self):  # pragma: no cover (only for debugging)
        return '[' + ', '.join(repr(case) for case in self.cases) + ']'

    def add_group(self, escaped, num):
        self.string += escaped
        self.cases[-1].add_part(num)

    def add_literal(self, escaped, string):
        self.string += escaped
        self.cases[-1].add_part(string)

    def add_escape(self, escaped, pyescaped):
        self.string += escaped
        if pyescaped in [self.CASE_ASIS, self.CASE_LOWER, self.CASE_UPPER]:
            self.add_case(pyescaped, self.CASE_FLIP_NONE)
        elif pyescaped in [self.CASE_FLIP_LOWER, self.CASE_FLIP_UPPER]:
            self.add_case(self.cases[-1].get_case_set(), pyescaped)
        else:
            match = re.match('\\(\\?:\\\\(\\d+)\\)', pyescaped)
            if match:
                self.cases[-1].add_part(int(match.group(1)))
            else:
                raise SedException(
                    '', 'Programming error. Escape sequence in replacement string invalid.')

    def add_case(self, case_set, case_flip):
        if self.cases[-1].is_empty():
            self.cases.pop()
        self.cases.append(CaseSetter(case_set, case_flip))

    def expand(self, match):
        result = ''
        for case in self.cases:
            result += case.expand(match)
        return result


class CaseSetter(object):

    def __init__(self, case_set, case_flip):
        self.case_set = case_set
        self.case_set_fn = self.MAP.get(case_set)
        self.case_flip = case_flip
        self.case_flip_fn = self.MAP.get(case_flip)
        self.parts = []

    def __str__(self):  # pragma: no cover (only for debugging)
        return self.case_set + self.case_flip + ''.join(
                    (part
                     if type(part) == str or PY2 and type(part) == unicode
                     else '\\+str(part)')
                    for part in self.parts)

    def __repr__(self):  # pragma: no cover (only for debugging)
        return self.__str__()

    def is_empty(self):
        return len(self.parts) == 0

    def get_case_set(self):
        return self.case_set

    def add_part(self, part):
        if (type(part) == str or PY2 and type(part) == unicode) \
           and len(self.parts) > 0 \
           and type(self.parts[-1]) == type(part):
            self.parts[-1] += part
        else:
            self.parts.append(part)

    def expand(self, match):
        txt = ''
        for part in self.parts:
            if type(part) == int:
                txt += match.group(part) or ''
            else:
                txt += part
        return self.case_flip_fn(self.case_set_fn(txt))

    MAP = {
        Replacement.CASE_LOWER: (lambda txt: txt.lower()),
        Replacement.CASE_UPPER: (lambda txt: txt.upper()),
        Replacement.CASE_ASIS: (lambda txt: txt),
        Replacement.CASE_FLIP_LOWER: (lambda txt: txt[0].lower() + txt[1:]
                                      if txt else ''),
        Replacement.CASE_FLIP_UPPER: (lambda txt: txt[0].upper() + txt[1:]
                                      if txt else '')
        # CASE_FLIP_NONE: keep_as_is, ## same as CASE_ASIS!!!
    }


# The two following classes implement the regexps for PythonSed.
# The offer services for the empty regexp which is a short-hand for
# 'repeat the last executed regexp again" and real regexp and the
# substitution of those used in the s command.


class SedRegexpEmpty(object):

    def __init__(self, position, delim, address=True):
        self.position = position
        self.delim = delim
        self.pattern = ''
        self.address = address

    def matches(self, strg):
        if SedRegexp.last_regexp is None:
            raise SedException(self.position,
                               'No regexp to match in place of empty regexp')
        return SedRegexp.last_regexp.matches(strg)

    def subn(self, replacement, strng, globally, count, sed_compatible):
        if SedRegexp.last_regexp is None:
            raise SedException(self.position,
                               'No regexp to match in place of empty regexp')
        return SedRegexp.last_regexp.subn(
            replacement, strng, globally, count, sed_compatible)

    def __str__(self):  # pragma: no cover (only for debugging)
        return self.toString()

    def toString(self):  # pragma: no cover (only for debugging)
        return ('' if self.delim == '/' or not self.address else '\\'
                + self.delim + self.delim)

    def __repr__(self):  # pragma: no cover (only for debugging)
        return self.__str__()

    def process_flags_and_dollars(self):
        pass

    def set_multi_line(self):
        raise SedException(self.position,
                           'Using multi-line flag with an empty ' +
                           'regular expression is not possible')

    def set_ignore_case(self):
        raise SedException(self.position,
                           'Using ignore case flag with an empty ' +
                           'regular expression is not possible')


class SedRegexp(object):
    last_regexp = None

    def __init__(self, position, delim, pattern,
                 py_pattern, dollars, address=True):
        self.position = position
        self.delim = delim
        self.pattern = pattern
        self.py_pattern = py_pattern
        self.dollars = dollars
        self.address = address
        self.multi_line = False
        self.ignore_case = False
        self.flags = ''
        self.compiled = None

    def __str__(self):  # pragma: no cover (only for debugging)
        return self.toString()

    def toString(self):  # pragma: no cover (only for debugging)
        result = '' if self.delim == '/' else '\\'
        result += self.delim + self.pattern + self.delim
        if self.address:
            result += 'I' if self.ignore_case else ''
            result += 'M' if self.multi_line else ''
        return result

    def __repr__(self):  # pragma: no cover (only for debugging)
        return self.__str__()

    def set_multi_line(self):
        self.multi_line = True

    def set_ignore_case(self):
        self.ignore_case = True

    def process_flags_and_dollars(self):
        self.flags = '(?'
        if self.multi_line:
            self.flags += 'm'
        else:
            self.flags += 's'
        if self.ignore_case:
            self.flags += 'i'
        self.flags += ')'
        # We have to process the dollar signs from
        # the back to the front, because otherwise
        # the index of the dollar signs would not fit
        # anymore after our first change in the pattern.
        # Once we processed them - or if we do not have
        # sed compatibility requested, the list is empty!
        while len(self.dollars) > 0:
            dollar = self.dollars.pop()
            if dollar + 1 < len(self.py_pattern) and \
               self.py_pattern[dollar + 1] not in '|)':
                # we have a dollar sign to be taken literally -> change to \\$
                self.py_pattern = (self.py_pattern[0:dollar] + '\\'
                                   + self.py_pattern[dollar:])
            elif not self.multi_line:
                # we have a dollar sign but not multi-line -> change to \\Z
                self.py_pattern = (self.py_pattern[0:dollar] + '\\Z'
                                   + self.py_pattern[dollar + 1:])
        try:
            self.compiled = re.compile(self.flags + self.py_pattern)
        except re.error as e:
            raise SedException(
                self.position,
                'Invalid regex {escaped}{delim}{pattern}{delim} ' +
                '(translated to """{py_pattern}"""): {err}',
                escaped='' if self.delim == '/' else '\\',
                delim=self.delim,
                pattern=self.pattern,
                py_pattern=self.flags + self.py_pattern,
                err=str(e))

    def matches(self, strng):
        SedRegexp.last_regexp = self
        try:
            match = self.compiled.search(strng)
            return match is not None
        except Exception as e:
            raise SedException(
                self.position,
                'Error when searching with regex {escaped}{delim}{pattern}{delim}' +
                ' (translated to """{py_pattern}"""): {err}',
                escaped='' if self.delim == '/' else '\\',
                delim=self.delim,
                pattern=self.pattern,
                py_pattern=self.flags + self.py_pattern,
                err=str(e))

    def subn(self, replacement, strng, globally, count, sed_compatible):
        # re.sub() extended:
        # - an unmatched group returns an empty string rather than None
        #   (http://gromgull.net/blog/2012/10/python-regex-unicode-and-brokenness/)
        # - the nth occurrence is replaced rather than the nth first ones
        #   (https://mail.python.org/pipermail/python-list/2008-December/475132.html)
        SedRegexp.last_regexp = self

        class Nth(object):

            def __init__(self):
                self.matches = 0
                self.prevmatch_end = -1

            def __call__(self, matchobj):
                try:
                    # check for 'empty match' that should not been replaced
                    if sed_compatible \
                       and matchobj.group(0) == '' \
                       and matchobj.start(0) == self.prevmatch_end:
                        # with sed compatablilty this is not really a match
                        # thus we do not insert the replacement string.
                        return ''
                    else:
                        self.matches += 1
                        if self.matches == count \
                           or globally and self.matches > count:
                            # if this is a match we want to replace, calculate the
                            # replacement string for the current match and return it
                            return replacement.expand(matchobj)
                        else:
                            # otherwise just return what was matched instead,
                            # without any changes
                            return matchobj.group(0)
                finally:
                    # remember this match's end position for our
                    # 'empty match'-check the next time around.
                    self.prevmatch_end = matchobj.end(0)

        try:
            strng_res, nsubst = self.compiled.subn(
                Nth(), strng, 0 if globally or sed_compatible else count)
        except re.error as e:
            raise SedException(
                self.position,
                'Error substituting regex {escaped}{delim}{pattern}{delim} ' +
                '(translated to """{py_pattern}"""): {err}',
                escaped='' if self.delim == '/' else '\\',
                delim=self.delim,
                pattern=self.pattern,
                py_pattern=self.flags + self.py_pattern,
                err=str(e))
        # nsubst is the number of subst which would
        # have been made without the redefinition
        return (nsubst >= count), strng_res


# The following classes implement the various forms of addresses and address ranges.
# There is a specialized class for each kind of address range to avoid unneccessary
# if-elif-cascades during processing of the input to optimise runtime.


class AddressLast(object):

    def __init__(self, sed):
        self.sed = sed

    def __str__(self):  # pragma: no cover (only for debugging)
        return '$'

    def __repr__(self):  # pragma: no cover (only for debugging)
        return self.__str__()

    def matches(self):
        return self.sed.is_last_line()


class AddressZero(object):
    """ This class is never actually used during runtime. Instances of this
        class only exist during the compilation of addresses found in the script.
        Their instances are then replaced with instances of the class
        AddressRangeZeroToRegexp which is the only valid application of a 0-address.
    """

    def __init__(self, sed):
        self.sed = sed

    def __str__(self):  # pragma: no cover (only for debugging)
        return '0'

    def __repr__(self):  # pragma: no cover (only for debugging)
        return self.__str__()

    # AddressZero objects only exists during compilation and are
    # never actually used and thus don't need a method matches()
    # def matches(self):
    #     return True


class AddressRegexp(object):
    """ This address implenentation activates if a regexp can be matched
        against the pattern space.
    """

    def __init__(self, sed, regexp):
        self.sed = sed
        self.regexp = regexp

    def __str__(self):  # pragma: no cover (only for debugging)
        return str(self.regexp)

    def __repr__(self):  # pragma: no cover (only for debugging)
        return self.__str__()

    def matches(self):
        return self.regexp.matches(self.sed.PS)


class AddressNum(object):
    """ This address implementation activates if a certain line number
        is reached in the input stream or current input file (if the files
        are processed separately).
    """

    def __init__(self, sed, num):
        self.sed = sed
        self.num = num

    def __str__(self):  # pragma: no cover (only for debugging)
        return str(self.num)

    def __repr__(self):  # pragma: no cover (only for debugging)
        return self.__str__()

    def matches(self):
        return self.sed.file_line_no() == self.num


class AddressStep(object):
    """ This address implementation activates, if a certain line number is reached
        in the input or the line number is bigger than that and the difference modulo
        a given step-number is zero.
        It implements address of the kind <start>~<step> i.e. 5~3 which would activate
        on 5, 8, 11, 14, ...
    """

    def __init__(self, sed, num, step):
        self.sed = sed
        self.num = num
        self.step = step

    def __str__(self):  # pragma: no cover (only for debugging)
        return str(self.num) + '~' + str(self.step)

    def __repr__(self):  # pragma: no cover (only for debugging)
        return self.__str__()

    def matches(self):
        line_no = self.sed.file_line_no()
        if line_no < self.num:
            return False
        return (line_no - self.num) % self.step == 0


class AddressRangeNone(object):
    """ This address range implements a 'alway-active' dummy range and is used for
        all commands that do not have an address associated with it.
    """

    def __init__(self):
        self.first_line = True

    def is_active(self):
        return True

    def __str__(self):  # pragma: no cover (only for debugging)
        return ''

    def __repr__(self):  # pragma: no cover (only for debugging)
        return ''

    def from_as_str(self):  # pragma: no cover (only for debugging)
        return ''

    def to_as_str(self):  # pragma: no cover (only for debugging)
        return ''

    def negated_as_str(self):  # pragma: no cover (only for debugging)
        return ''


class AddressRangeFake(object):
    """ This address range class implements a fake address range that is actually only
        a from-address without a to-address. It activates only for the lines, the stored
        from-address is active for.
    """

    def __init__(self, from_addr):
        self.from_addr = from_addr
        self.first_line = True
        self.set_negate(False)

    def set_negate(self, negate):
        self.active_return = not negate
        self.inactive_return = negate

    def is_active(self):
        if self.from_addr.matches():
            return self.active_return
        else:
            return self.inactive_return

    def __str__(self):  # pragma: no cover (only for debugging)
        return str(self.from_addr) + self.negated_as_str()

    def __repr__(self):  # pragma: no cover (only for debugging)
        return self.__str__()

    def from_as_str(self):  # pragma: no cover (only for debugging)
        return str(self.from_addr)

    def to_as_str(self):  # pragma: no cover (only for debugging)
        return ''

    def negated_as_str(self):  # pragma: no cover (only for debugging)
        if self.active_return:
            return ''
        else:
            return '!'


class AddressRange(object):
    """ This is the abstract base-class of the other address range classes.
        No instance of this class is ever created.
    """

    def __init__(self, from_addr, exclude):
        self.from_addr = from_addr
        self.sed = self.from_addr.sed
        self.exclude = exclude
        self.active = False
        self.set_negate(False)

    def set_negate(self, negate):
        self.first_line_default = negate
        self.first_line = self.first_line_default
        self.exclude_return = self.exclude == negate
        self.active_return = not negate
        self.inactive_return = negate

    def __str__(self):  # pragma: no cover (only for debugging)
        return (self.from_as_str() + ',' +
                self.to_as_str() +
                self.negated_as_str())

    def __repr__(self):  # pragma: no cover (only for debugging)
        return self.__str__()

    def from_as_str(self):  # pragma: no cover (only for debugging)
        return str(self.from_addr)

    def to_as_str(self):  # pragma: no cover (only for debugging)
        return '---'

    def negated_as_str(self):  # pragma: no cover (only for debugging)
        if self.active_return:
            return ''
        else:
            return '!'

    def exclude_as_str(self):  # pragma: no cover (only for debugging)
        if self.exclude:
            return '-'
        else:
            return ''


class AddressRangeToNum(AddressRange):
    """ This address range class implements an address range that starts with
        a given from-address and continues to a certain line number within the input.
    """

    def __init__(self, from_addr, num, exclude):
        super(AddressRangeToNum, self). __init__(from_addr, exclude)
        self.num = num
        self.last_line_no = 0

    def is_active(self):
        if self.active:
            self.first_line = self.first_line_default
            curr_line_no = self.sed.file_line_no()
            if self.last_line_no < curr_line_no:
                self.active = False
                return self.inactive_return
            elif self.last_line_no == curr_line_no:
                self.active = False
                return self.exclude_return
            else:
                return self.active_return
        elif self.from_addr.matches():
            self.first_line = True
            self.last_line_no = self.calc_last_line()
            self.active = True
            return self.active_return
        else:
            return self.inactive_return

    def calc_last_line(self):  # num
        return self.num

    def to_as_str(self):  # pragma: no cover (only for debugging)
        return self.exclude_as_str() + str(self.num)


class AddressRangeToCount(AddressRangeToNum):
    """ This address range class implements the address range that starts with
        a given from-address and ends after a certain number of lines from the input.
    """

    def calc_last_line(self):  # count
        return self.sed.file_line_no() + self.num

    def to_as_str(self):  # pragma: no cover (only for debugging)
        return self.exclude_as_str() + '+' + str(self.num)


class AddressRangeToMultiple(AddressRangeToNum):
    """ This address range class implements an address range that starts with
        a given from-address and ends once the input line number becomes a
        multiple of the specified multiple number.
        It implements address ranges of the kind <from-addr>,~<multiple>
    """

    def calc_last_line(self):
        line_no = self.sed.file_line_no()
        return line_no + self.num - (line_no % self.num)

    def to_as_str(self):  # pragma: no cover (only for debugging)
        return self.exclude_as_str() + '~' + str(self.num)


class AddressRangeToLastLine(AddressRange):
    """ This address range class implemnents an address range that starts with
        a given from-address and ends once in input reaches the last line.
    """

    def is_active(self):
        if self.active:
            self.first_line = self.first_line_default
            if self.sed.is_last_line():
                self.active = False
                return self.exclude_return
            else:
                return self.active_return
        elif self.from_addr.matches():
            self.first_line = True
            self.active = True
            return self.active_return
        else:
            return self.inactive_return

    def to_as_str(self):  # pragma: no cover (only for debugging)
        return self.exclude_as_str() + '$'


class AddressRangeZeroToRegexp(AddressRange):
    """ This address range implements the special address range 0,/regexp/, that
        is active on the first line of input already and ends if the pattern space
        matches the specified regexp.
        This allows to have the first line end the address range which would otherwise
        not be possible, since an address range will always match the start AND the end
        line. The only two exceptions being this Zero-to-Regexp-address and an address
        range activating on the last line of input.
    """

    def __init__(self, from_addr, regexp, exclude):
        super(AddressRangeZeroToRegexp, self). __init__(from_addr, exclude)
        self.regexp = regexp
        self.active = True
        self.next_first_line = True

    def is_active(self):
        if self.active:
            self.first_line = self.next_first_line
            self.next_first_line = False
            if self.regexp.matches(self.sed.PS):
                self.active = False
                return self.exclude_return
            else:
                return self.active_return
        else:
            self.first_line = True
            return self.inactive_return

    def to_as_str(self):  # pragma: no cover (only for debugging)
        return self.exclude_as_str() + str(self.regexp)


class AddressRangeToRegexp(AddressRange):
    """ This address range class implements an address range that starts with
        a given from-address and ends when the pattern space matches the given
        regexp.
    """

    def __init__(self, from_addr, regexp, exclude):
        super(AddressRangeToRegexp, self). __init__(from_addr, exclude)
        self.regexp = regexp

    def is_active(self):
        if self.active:
            self.first_line = self.first_line_default
            if self.regexp.matches(self.sed.PS):
                self.active = False
                return self.exclude_return
            else:
                return self.active_return
        elif self.from_addr.matches():
            self.first_line = True
            self.active = True
            return self.active_return
        else:
            return self.inactive_return

    def to_as_str(self):  # pragma: no cover (only for debugging)
        return self.exclude_as_str() + str(self.regexp)


# All errors in PythonSed are reported through the following exception class


class SedException(Exception):
    """ Implements the error reporting exception in PythonSed.
    """

    def __init__(self, position, message, **params):
        if len(position) > 0:
            self.message = 'sed.py error: {pos}: {msg}'.format(
                pos=position, msg=message.format(**params))
        else:
            self.message = 'sed.py error: {msg}'.format(msg=message.format(**params))

    def __str__(self):  # pragma: no cover (just used in IDE)
        return self.message


# -- Main -------------------------------------------


def do_helphtml():  # pragma: no cover (interactive code not testable with pyunittest)
    if os.path.isfile('sed.html'):
        helpfile = 'sed.html'
    else:
        helpfile = 'https://www.gnu.org/software/sed/manual/sed.html'
    webbrowser.open(helpfile, new=2)


class Filename(object):
    def __init__(self, encoding, filename):
        self.encoding = encoding
        self.filename = filename


class Literal(object):
    def __init__(self, encoding, literal):
        self.encoding = encoding
        self.literal = literal


class ParseArguments(object):

    def __init__(self):
        self.default_encoding = DEFAULT_ENCODING
        self.encoding = None

        parser = argparse.ArgumentParser(
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description=BRIEF,
            epilog="""\
Option -c can be repeated multiple times. The first is going to be used as default \
encoding and for stdout output, writing to files (commands w and W) and reading from \
files (commands r and R). For script literals (-e), script files (-f) and input files \
the last preceding -c option is used to define that part's encoding.

Options -e and -f can be repeated multiple times and add to the commands \
executed for each line of input in the sequence they are specified.

If neither -e nor -f is given, the first positional parameter is taken as \
the script, as if it had been prefixed with -e.""")
        parser.add_argument(
            '-H', '--htmlhelp',
            help='open html help page in web browser',
            action='store_true',
            default=False,
            dest='do_helphtml')
        parser.add_argument(
            '-v', '--version',
            help='display version',
            action='store_true',
            default=False,
            dest='version')
        parser.add_argument(
            '-c', '--encoding',
            help='input encoding',
            action='store',
            type=self.encoding_arg,
            default=DEFAULT_ENCODING)
        parser.add_argument(
            '-f', '--file',
            help='add script commands from file',
            action='append',
            dest='scripts',
            default=[],
            type=self.file_arg,
            metavar='file')
        parser.add_argument(
            '-e', '--expression',
            help='add script commands from string',
            action='append',
            dest='scripts',
            default=[],
            type=self.literal_arg,
            metavar='string')
        parser.add_argument(
            '-i', '--in-place',
            nargs='?',
            help='change input files in place',
            type=self.literal_arg,
            dest='in_place',
            metavar='backup suffix',
            default=0)
        parser.add_argument(
            '-n', '--quiet', '--silent',
            help='print only if requested',
            action='store_true',
            default=False,
            dest='no_autoprint')
        parser.add_argument(
            '-s', '--separate',
            help='consider input files as separate files ' +
            'instead of a continuous stream',
            action='store_true',
            default=False,
            dest='separate')
        parser.add_argument(
            '-p', '--python-syntax',
            help='Python regexp syntax',
            action='store_false',
            default=True,
            dest='sed_compatible')
        parser.add_argument(
            '-r', '-E', '--regexp-extended',
            help='extended regexp syntax',
            action='store_true',
            default=False,
            dest='regexp_extended')
        parser.add_argument(
            '-l', '--line-length',
            help='line length to be used by l command',
            dest='line_length',
            default=70,
            type=int)
        parser.add_argument(
            '-d', '--debug',
            help='dump script and annotate execution on stderr',
            action='store',
            type=int,
            default=0,
            dest='debug')
        parser.add_argument(
            'targets',
            nargs='*',
            type=self.file_arg,
            help='files to be processed (defaults to stdin if not specified)',
            default=[])
        self.args = parser.parse_args()
        if (not self.args.version and
            len(self.args.scripts) == 0 and
                len(self.args.targets) == 0):
            parser.print_help()
            raise SedException('', 'No script specified.')

    def __getattr__(self, name):
        if name in self.args:
            return self.args.__getattribute__(name)
        raise AttributeError('Attribute {name} not found'.format(name=name))

    def get_encoding(self):
        if self.encoding:
            return self.encoding
        else:
            return self.default_encoding

    def encoding_arg(self, encoding):
        if self.encoding is None:
            self.default_encoding = encoding
        self.encoding = encoding
        return encoding

    def literal_arg(self, script_literal):
        return Literal(self.get_encoding(), script_literal)

    def file_arg(self, filename):
        return Filename(self.get_encoding(), filename)


def main():
    exit_code = 0
    encoding = DEFAULT_ENCODING
    try:
        args = ParseArguments()
        encoding = args.default_encoding

        if args.version:
            DEBUG('{brief}', brief=BRIEF)
            DEBUG('Version: {vers}', vers=VERSION)
            return 0
        elif args.do_helphtml:  # pragma: no cover (interactive code can not be tested)
            do_helphtml()
            return 0
        sed = Sed()
        sed.encoding = encoding
        sed.no_autoprint = args.no_autoprint
        sed.regexp_extended = args.regexp_extended

        if args.in_place is None:
            sed.in_place = ''
        elif isinstance(args.in_place, Literal):
            sed.in_place = make_unicode(args.in_place.literal, args.in_place.encoding)
        else:
            sed.in_place = None

        sed.line_length = args.line_length
        sed.debug = args.debug
        sed.separate = args.separate
        sed.sed_compatible = args.sed_compatible
        targets = args.targets
        scripts = args.scripts
        if len(scripts) == 0:
            # at this point we know targets is
            # not empty because that was checked
            # in ParseArguments.__init__() already
            scripts = targets.pop(0)
            scripts = [Literal(scripts.encoding, scripts.filename)]
        for script in scripts:
            if isinstance(script, Filename):
                sed.load_script(script.filename, encoding=script.encoding)
            else:
                sed.load_string(script.literal, encoding=script.encoding)
        targets = list((target.encoding, target.filename) for target in targets)
        sed.apply(targets, output=sys.stdout)
        exit_code = sed.exit_code
    except SedException as e:
        DEBUG('{msg}', msg=e.message)
        exit_code = 1
    except:  # noqa: E722  # pragma: no cover (only happening for programming errors)
        byteStream = BytesIO()
        traceback.print_exception(*sys.exc_info(), file=byteStream)
        sys.stderr.write(make_unicode(byteStream.getvalue(), encoding))
        del byteStream
        exit_code = 1
    return exit_code


if __name__ == '__main__':
    sys.exit(main())  # pragma: no cover (not executed in unittest)
