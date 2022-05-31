# -*- coding: utf-8 -*-
"""Utility for PythonSed unittest testcases"""
from __future__ import print_function, unicode_literals

from io import open as open, StringIO
import codecs
import locale
import logging
import os
import shutil
import sys
import tempfile
import unittest
import pytest

from stash.tests.stashtest import StashTestCase

ENCODING = 'utf-8'
PY2 = sys.version_info[0] == 2
if PY2:
    import Tkinter

    def make_unicode(strg, encoding):
        if type(strg) == str:
            return unicode(strg, encoding)
        else:
            return strg

else:

    class unicode(object):  # @ReservedAssignment
        pass

    def make_unicode(strg, encoding):
        if type(strg) == bytes:
            return strg.decode(encoding)
        else:
            return strg

    def unichr(char):  # @ReservedAssignment
        return chr(char)


class PythonSedTestCase(StashTestCase):
    """A test case implementing utility methods and tests for testing PythonSed"""

    def setUp(self):
        StashTestCase.setUp(self)
        self.temp_dir = tempfile.mkdtemp(prefix='sed_unittest.')

    def tearDown(self):
        StashTestCase.tearDown(self)
        shutil.rmtree(self.temp_dir)

    def create_tempfile(self, encoding, prefix, content):  # expects unicode for content
        (fd, name) = tempfile.mkstemp(dir=self.temp_dir, prefix=prefix)
        with os.fdopen(fd, 'wb') as fle:
            fle.write(codecs.getencoder(encoding)(content)[0])
        return name

    def run_test(
            self,
            debug=0,              # debug level (0..3)
            encoding=ENCODING,   # input encoding
            python_syntax=False,  # option -p/--python-syntax
            separate=False,       # option -s
            no_autoprint=False,   # option -n
            in_place=None,        # option -i value
            options=[],           # additional options
            scripts=[],           # literal script strings (as list) and file names (as string)
            inputs=[],            # literal input strings (as list) and file names (as string)
            stdin=None,           # stdin input to command
            redirect=None,        # pipe stdout to this file
            stdout=None,          # expected output to stdout
            stderr=None,          # expected output to stderr
            output_files={},      # expected content of files written by the sed script
            inplace_content=[],   # results of inplace-editing
            exit_code=0,          # expected exit code
            ):
        args = ['PYTHONIOENCODING="UTF-8"', 'sed.py', '--encoding='+encoding]
        if debug > 0:
            args.append('--debug='+str(debug))

        if python_syntax:
            args.append('--python-syntax')

        if separate:
            args.append('-s')

        if no_autoprint:
            args.append('-n')

        if in_place is not None:
            args.append('--in-place'+("='"+str(in_place)+"'" if len(str(in_place)) > 0 else "''"))

        args.extend(options)

        script_index = 0
        for script in scripts:
            script_index += 1
            if type(script) == list:
                for lines in script:
                    if '\n' in lines:
                        args.extend(['-f',
                                     "'"+self.create_tempfile(
                                             encoding,
                                             'script-literal.{idx}.'.format(idx=script_index),
                                             make_unicode(lines, encoding))+"'"])
                    else:
                        args.extend(['-e', '"'+lines.replace('\\', '\\\\')
                                                    .replace('$','\\$')
                                                    .replace('"', '\\"')+'"'])
            elif type(script) == str or PY2 and type(script) == unicode:
                args.extend(['-f', "'"+script+"'"])
            else:
                file_name = self.create_tempfile(encoding,
                                                 'script-stream.{idx}.'.format(idx=script_index),
                                                 ''.join(script.readlines()))
                args.extend(['-f', "'"+file_name+"'"])

        processed_inputs = []
        input_index = 0
        for input in inputs:  # @ReservedAssignment
            input_index += 1
            if type(input) == list:
                processed_inputs.append(
                    self.create_tempfile(encoding, 'input-literal.{idx}.'.format(idx=input_index),
                                         '\n'.join(make_unicode(lne, encoding) for lne in input)))
            elif type(input) == str or PY2 and type(input) == unicode:
                processed_inputs.append(input)
            else:
                file_name = self.create_tempfile(encoding,
                                                 'input-stream.{idx}.'.format(idx=input_index),
                                                 ''.join(input.readlines()))
                processed_inputs.append(file_name)

        args.extend("'"+fle+"'" for fle in processed_inputs)

        if redirect is not None:
            args.extend(['>', "'"+redirect+"'"])

        cmd = ' '.join(args)

        actual_exit_code, actual_stdout, actual_stderr = self.run_command_2(cmd, stdin_text=stdin)

        result = []
        if actual_exit_code != exit_code:
            result.append('Expected exit code was {exp} but the actual exit code was {act}'
                          .format(exp=exit_code, act=actual_exit_code))
            result.append('')
            if stderr is None:
                result.extend(self.check_output(encoding, 'stderr', '', actual_stderr))

        if stdout is not None:
            result.extend(self.check_output(encoding, 'stdout', stdout, actual_stdout))

        if stderr is not None:
            result.extend(self.check_output(encoding, 'stderr', stderr, actual_stderr))

        for (file_name, expected_content) in output_files.items():
            file_name = os.path.join(self.temp_dir, file_name)
            if os.path.exists(file_name):
                with open(file_name, 'rt', encoding=encoding) as f:
                    file_content = f.read()
            else:
                file_content = []
            result.extend(self.check_output(encoding, file_name,
                                            make_unicode(expected_content, encoding),
                                            file_content))

        if in_place is not None:
            if type(processed_inputs) == str or PY2 and type(processed_inputs) == unicode:
                processed_inputs = [processed_inputs]
            if type(processed_inputs) != list:
                raise ValueError('Invalid inputs list')
            if type(inplace_content) != list:
                raise ValueError('Invalid inplace_content list')
            if len(processed_inputs) != len(inplace_content):
                raise ValueError('List of input files and list of expected edited input ' +
                                 'file content must be of same size')
            in_place = make_unicode(in_place, encoding)
            for i in range(len(processed_inputs)):
                file_name = processed_inputs[i]
                if len(in_place) > 0:
                    if '*' in in_place:
                        bkup_file_name = in_place.replace('*', os.path.basename(file_name))
                        if '/' not in bkup_file_name:
                            bkup_file_name = os.path.join(os.path.dirname(file_name),
                                                          bkup_file_name)
                    else:
                        bkup_file_name = file_name+in_place
                    if not os.path.exists(bkup_file_name):
                        result.append('Backup file '+bkup_file_name+' is missing!')
                expected_content = inplace_content[i]
                if os.path.exists(file_name):
                    with open(file_name, 'rt', encoding=encoding) as f:
                        file_content = f.read()
                else:
                    file_content = []
                result.extend(self.check_output(encoding, file_name,
                                                expected_content, file_content))

        if len(result) > 0:
            try:
                result = '\nCommand was: '+cmd+'\n'+'\n'.join(result)
                self.fail(result)
            except TypeError:
                self.fail(str(result))

    def make_list(self, encoding, content):
        if type(content) == str or PY2 and type(content) == unicode:
            if len(content) == 0:
                return []
            content = make_unicode(content, encoding)
            if content.endswith('\n'):
                return list(lne+'\n' for lne in content[:-1].split('\n'))
            else:
                return list(lne+'\n' for lne in content.split('\n'))
        elif type(content) == list:
            return list(make_unicode(lne, encoding) for lne in content)
        raise ValueError('Programming error: invalid content parameter type ({}) for make_list'
                         .format(type(content)))

    def check_output(self, encoding, content_name, expected_content, actual_content):
        MISSING_MARKER = '<missing>'
        UNEXPECTED_MARKER = '<unexpected>'

        list1 = self.make_list(encoding, expected_content)
        list2 = self.make_list(encoding, actual_content)

        content_name = os.path.basename(content_name)
        tag1 = 'expected '+content_name
        tag2 = 'actual '+content_name

        max_lst_len = max(len(list1), len(list2))
        if max_lst_len == 0:
            return []

        # make sure both lists have same length
        list1.extend([None] * (max_lst_len - len(list1)))
        list2.extend([None] * (max_lst_len - len(list2)))

        max_txt_len_1 = max(list(len(UNEXPECTED_MARKER)
                                 if txt is None
                                 else 3*len(txt)-2*len(txt.rstrip('\r\n'))
                                 for txt in list1)+[len(tag1)])
        max_txt_len_2 = max(list(len(MISSING_MARKER)
                                 if txt is None
                                 else 3*len(txt)-2*len(txt.rstrip('\r\n'))
                                 for txt in list2)+[len(tag2)])

        diff = ['']
        equal = True
        diff.append('|  No | ? | {tag1:<{txtlen1}.{txtlen1}s} | {tag2:<{txtlen2}.{txtlen2}s} |'
                    .format(tag1=tag1, tag2=tag2, txtlen1=max_txt_len_1, txtlen2=max_txt_len_2))
        for i, (x, y) in enumerate(zip(list1, list2)):
            if x != y:
                equal = False
                if x is not None and y is not None and x.rstrip('\r\n') == y.rstrip('\r\n'):
                    x = x.replace('\n', '\\n').replace('\r', '\\r')
                    y = y.replace('\n', '\\n').replace('\r', '\\r')
            diff.append('| {idx:>3d} | {equal:1.1s} | {line1:<{txtlen1}.{txtlen1}s} | {line2:<{txtlen2}.{txtlen2}s} |'  # noqa: E501
                        .format(idx=i+1,
                                equal=(' ' if x == y else '*'),
                                txtlen1=max_txt_len_1,
                                txtlen2=max_txt_len_2,
                                line1=UNEXPECTED_MARKER
                                      if x is None
                                      else x.rstrip('\r\n'),  # .replace(' ', '\N{MIDDLE DOT}'),
                                line2=MISSING_MARKER
                                      if y is None
                                      else y.rstrip('\r\n')))  # .replace(' ', '\N{MIDDLE DOT}')))

        return [] if equal else diff

    def test_001_syntax_terminating_commands_all_but_y_1(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""1 { p }
2 { s/abc/&&/ }
"""]],
            inputs=[[
"""abc1
abc2
"""]],
            stdout=(
"""abc1
abc1
abcabc2
"""),
            stderr='',
            exit_code=0,
            )

    def test_002_syntax_terminating_commands_all_but_y_2(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""1 { p ; }
2 { s/abc/&&/ ;  }
"""]],
            inputs=[[
"""abc1
abc2
"""]],
            stdout=(
"""abc1
abc1
abcabc2
"""),
            stderr='',
            exit_code=0,
            )

    def test_003_syntax_terminating_commands_all_but_y_3(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""1 p # comment
2 s/abc/&&/ # comment
"""]],
            inputs=[[
"""abc1
abc2
"""]],
            stdout=(
"""abc1
abc1
abcabc2
"""),
            stderr='',
            exit_code=0,
            )

    def test_004_syntax_terminating_commands_y_1(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[["""1 { y/abc/def/ }"""]],
            inputs=[[
"""abc
"""]],
            stdout=(
"""def
"""),
            stderr='',
            exit_code=0,
            )

    def test_005_syntax_terminating_commands_y_2(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[["""1 { y/abc/def/ ; }"""]],
            inputs=[[
"""abc
"""]],
            stdout=(
"""def
"""),
            stderr='',
            exit_code=0,
            )

    def test_006_syntax_terminating_commands_y_3(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[["""1 y/abc/def/ # comment"""]],
            inputs=[[
"""abc
"""]],
            stdout=(
"""def
"""),
            stderr='',
            exit_code=0,
            )

    def test_007_syntax_terminating_commands_4_no_space_at_end_of_line(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[["""p; p"""]],
            inputs=[[
"""a
"""]],
            stdout=(
"""a
a
a
"""),
            stderr='',
            exit_code=0,
            )

    def test_008_syntax_terminating_commands_5_one_space_at_end_of_line(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[["""p; p """]],
            inputs=[[
"""a
"""]],
            stdout=(
"""a
a
a
"""),
            stderr='',
            exit_code=0,
            )

    def test_009_syntax_terminating_commands_6_no_space_at_end_of_line(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[["""p; p;"""]],
            inputs=[[
"""a
"""]],
            stdout=(
"""a
a
a
"""),
            stderr='',
            exit_code=0,
            )

    def test_010_syntax_terminating_commands_7_one_space_at_end_of_line(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[["""p; p; """]],
            inputs=[[
"""a
"""]],
            stdout=(
"""a
a
a
"""),
            stderr='',
            exit_code=0,
            )

    def test_011_syntax_terminating_commands_8(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[["""1"""]],
            inputs=[[
"""a
"""]],
            stdout='',
            stderr='sed.py error: -e #1 line 1 char 1: Address without a command\n',
            exit_code=1,
            )

    def test_012_syntax_terminating_commands_9(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[['1,']],
            inputs=[[
"""a
"""]],
            stdout='',
            stderr='sed.py error: -e #1 line 1 char 4: Invalid address' +
                   ' specification: missing to-address\n',
            exit_code=1,
            )

    def test_013_syntax_terminating_commands_10(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[["""1,2"""]],
            inputs=[[
"""a
"""]],
            stdout='',
            stderr='sed.py error: -e #1 line 1 char 1: Address without a command\n',
            exit_code=1,
            )

    def test_014_syntax_terminating_commands_aic(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#n
i\\
foo # no comment inside i argument
i\\
bar ; nor separator inside i argument
i\\
egg } nor end of block inside i argument
a\\
foo # no comment inside a argument
a\\
bar ; nor separator inside a argument
a\\
egg } nor end of block inside a argument
c\\
foo # no comment inside c argument
c\\
bar ; nor separator inside c argument
c\\
egg } nor end of block inside c argument
"""]],
            inputs=[[
"""x
"""]],
            stdout=(
"""foo # no comment inside i argument
bar ; nor separator inside i argument
egg } nor end of block inside i argument
foo # no comment inside c argument
foo # no comment inside a argument
bar ; nor separator inside a argument
egg } nor end of block inside a argument
"""),
            stderr='',
            exit_code=0,
            )

    def test_015_regexp_address_separators(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#n
h
g; /a/p
g; \\xaxp
g; \\a\\aap
"""]],
            inputs=[[
"""abc
"""]],
            stdout=(
"""abc
abc
abc
"""),
            stderr='',
            exit_code=0,
            )

    def test_016_regexp_address_flags(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#n
/abc/p
/ABC/Ip
"""]],
            inputs=[[
"""abc
ABC
"""]],
            stdout=(
"""abc
abc
ABC
"""),
            stderr='',
            exit_code=0,
            )

    def test_017_regexp_address_address_range_with_flag(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#n
/abc/,/def/p
/abc/I,/def/p
/abc/,/def/Ip
/abc/I,/def/Ip
"""]],
            inputs=[[
"""abc
def
ABC
DEF
"""]],
            stdout=(
"""abc
abc
abc
abc
def
def
def
def
ABC
ABC
DEF
DEF
"""),
            stderr='',
            exit_code=0,
            )

    def test_018_empty_addresses_single_address(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#n
/a/p;//p
"""]],
            inputs=[[
"""a
b
a
b
"""]],
            stdout=(
"""a
a
a
a
"""),
            stderr='',
            exit_code=0,
            )

    def test_019_empty_addresses_address_range(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#n
/a/p;//,//p
"""]],
            inputs=[[
"""a
b
a
b
"""]],
            stdout=(
"""a
a
b
a
a
"""),
            stderr='',
            exit_code=0,
            )

    def test_020_PS_ending_with_a_line_break(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""s/.*/\\n/
s/$/X/g
"""]],
            inputs=[[
"""x
"""]],
            stdout=(
"""
X
"""),
            stderr='',
            exit_code=0,
            )

    def test_021_anchors_at_end_of_regexp_1_BRE(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#n
s/\\(abc\\)$/ABC/p
"""]],
            inputs=[[
"""abc$abc
"""]],
            stdout=(
"""abc$ABC
"""),
            stderr='',
            exit_code=0,
            )

    def test_022_anchors_at_end_of_regexp_1_ERE(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#nr
s/(abc)$/ABC/p
"""]],
            inputs=[[
"""abc$abc
"""]],
            stdout=(
"""abc$ABC
"""),
            stderr='',
            exit_code=0,
            )

    def test_023_anchors_at_end_of_regexp_2_BRE(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#n
s/\\(abc\\)\\($\\)/ABC/p
"""]],
            inputs=[[
"""abc$abc
"""]],
            stdout=(
"""abc$ABC
"""),
            stderr='',
            exit_code=0,
            )

    def test_024_anchors_at_end_of_regexp_2_ERE(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#nr
s/(abc)($)/ABC/p
"""]],
            inputs=[[
"""abc$abc
"""]],
            stdout=(
"""abc$ABC
"""),
            stderr='',
            exit_code=0,
            )

    def test_025_anchors_at_end_of_regexp_3_BRE(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#n
s/\\(abc\\)\\(X\\|$\\)/ABC/p
"""]],
            inputs=[[
"""abc$abc
"""]],
            stdout=(
"""abc$ABC
"""),
            stderr='',
            exit_code=0,
            )

    def test_026_anchors_at_end_of_regexp_3_ERE(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#nr
s/(abc)(X|$)/ABC/p
"""]],
            inputs=[[
"""abc$abc
"""]],
            stdout=(
"""abc$ABC
"""),
            stderr='',
            exit_code=0,
            )

    def test_027_anchors_at_end_of_regexp_4_BRE(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#n
s/\\(abc\\)\\($\\|X\\)/ABC/p
"""]],
            inputs=[[
"""abc$abc
"""]],
            stdout=(
"""abc$ABC
"""),
            stderr='',
            exit_code=0,
            )

    def test_028_anchors_at_end_of_regexp_4_ERE(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#nr
s/(abc)($|X)/ABC/p
"""]],
            inputs=[[
"""abc$abc
"""]],
            stdout=(
"""abc$ABC
"""),
            stderr='',
            exit_code=0,
            )

    def test_029_anchors_inside_regexp_BRE(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#n
s/.*\\(abc\\)$.*/\\1/p
"""]],
            inputs=[[
"""xabc$y
"""]],
            stdout=(
"""abc
"""),
            stderr='',
            exit_code=0,
            )

    def test_030_anchors_inside_regexp_ERE(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#nr
s/.*(abc)$.*/\\1/p
"""]],
            inputs=[[
"""xabc$y
"""]],
            stdout=(
"""abc
"""),
            stderr='',
            exit_code=0,
            )

    def test_031_anchors_at_start_of_regexp_1_BRE(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#n
s/^\\(abc\\)/ABC/p
"""]],
            inputs=[[
"""abc^abc
"""]],
            stdout=(
"""ABC^abc
"""),
            stderr='',
            exit_code=0,
            )

    def test_032_anchors_at_start_of_regexp_1_ERE(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#nr
s/^(abc)/ABC/p
"""]],
            inputs=[[
"""abc^abc
"""]],
            stdout=(
"""ABC^abc
"""),
            stderr='',
            exit_code=0,
            )

    def test_033_anchors_at_start_of_regexp_2_BRE(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#n
s/\\(^\\)\\(abc\\)/ABC/p
"""]],
            inputs=[[
"""abc^abc
"""]],
            stdout=(
"""ABC^abc
"""),
            stderr='',
            exit_code=0,
            )

    def test_034_anchors_at_start_of_regexp_2_ERE(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#nr
s/(^)(abc)/ABC/p
"""]],
            inputs=[[
"""abc^abc
"""]],
            stdout=(
"""ABC^abc
"""),
            stderr='',
            exit_code=0,
            )

    def test_035_anchors_at_start_of_regexp_3_BRE(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#n
s/\\(^\\|X\\)\\(abc\\)/ABC/p
"""]],
            inputs=[[
"""abc^abc
"""]],
            stdout=(
"""ABC^abc
"""),
            stderr='',
            exit_code=0,
            )

    def test_036_anchors_at_start_of_regexp_3_ERE(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#nr
s/(^|X)(abc)/ABC/p
"""]],
            inputs=[[
"""abc^abc
"""]],
            stdout=(
"""ABC^abc
"""),
            stderr='',
            exit_code=0,
            )

    def test_037_anchors_at_start_of_regexp_4_BRE(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#n
s/\\(X\\|^\\)\\(abc\\)/ABC/p
"""]],
            inputs=[[
"""abc^abc
"""]],
            stdout=(
"""ABC^abc
"""),
            stderr='',
            exit_code=0,
            )

    def test_038_anchors_at_start_of_regexp_4_ERE(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#nr
s/(X|^)(abc)/ABC/p
"""]],
            inputs=[[
"""abc^abc
"""]],
            stdout=(
"""ABC^abc
"""),
            stderr='',
            exit_code=0,
            )

    def test_039_anchors_inside_regexp_BRE(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#n
s/.*\\(abc\\)^.*/\\1/p
"""]],
            inputs=[[
"""xabc^y
"""]],
            stdout=(
"""abc
"""),
            stderr='',
            exit_code=0,
            )

    def test_040_anchors_inside_regexp_ERE(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#nr
s/.*(abc)^.*/\\1/p
"""]],
            inputs=[[
"""xabc^y
"""]],
            stdout=(
"""abc
"""),
            stderr='',
            exit_code=0,
            )

    def test_041_regexp_or(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#n
/a\\|b/p
/ab\\|cd/p
/\\(ab\\)\\|\\(cd\\)/p
"""]],
            inputs=[[
"""axy
xyb
abd
acd
ab
cd
"""]],
            stdout=(
"""axy
xyb
abd
abd
abd
acd
acd
acd
ab
ab
ab
cd
cd
"""),
            stderr='',
            exit_code=0,
            )

    def test_042_regexp_or_ERE(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#nr
/a|b/p
/ab|cd/p
/(ab)|(cd)/p
"""]],
            inputs=[[
"""axy
xyb
abd
acd
ab
cd
"""]],
            stdout=(
"""axy
xyb
abd
abd
abd
acd
acd
acd
ab
ab
ab
cd
cd
"""),
            stderr='',
            exit_code=0,
            )

    def test_043_regexp_BRE(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[["""s/ab+/cd/"""]],
            inputs=[[
"""ab+
"""]],
            stdout=(
"""cd
"""),
            stderr='',
            exit_code=0,
            )

    def test_044_regexp_BRE(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[["""s/ab\\+/cd/"""]],
            inputs=[[
"""abbb
"""]],
            stdout=(
"""cd
"""),
            stderr='',
            exit_code=0,
            )

    def test_045_regexp_ERE(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#r
s/ab+/cd/
"""]],
            inputs=[[
"""abbb
"""]],
            stdout=(
"""cd
"""),
            stderr='',
            exit_code=0,
            )

    def test_046_regexp_ERE(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#r
s/ab\\+/cd/
"""]],
            inputs=[[
"""ab+
"""]],
            stdout=(
"""cd
"""),
            stderr='',
            exit_code=0,
            )

    def test_047_regexp_BRE(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[["""s/ab?/cd/"""]],
            inputs=[[
"""ab?
"""]],
            stdout=(
"""cd
"""),
            stderr='',
            exit_code=0,
            )

    def test_048_regexp_BRE(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[["""s/ab\\?/cd/"""]],
            inputs=[[
"""a
"""]],
            stdout=(
"""cd
"""),
            stderr='',
            exit_code=0,
            )

    def test_049_regexp_ERE(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#r
s/ab?/cd/
"""]],
            inputs=[[
"""a
"""]],
            stdout=(
"""cd
"""),
            stderr='',
            exit_code=0,
            )

    def test_050_regexp_ERE(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#r
s/ab\\?/cd/
"""]],
            inputs=[[
"""ab?
"""]],
            stdout=(
"""cd
"""),
            stderr='',
            exit_code=0,
            )

    def test_051_regexp_BRE(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[["""s/ab*?/cd/"""]],
            inputs=[[
"""abbb?
"""]],
            stdout=(
"""cd
"""),
            stderr='',
            exit_code=0,
            )

    def test_052_regexp_BRE(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[["""s/ab+?/cd/"""]],
            inputs=[[
"""ab+?
"""]],
            stdout=(
"""cd
"""),
            stderr='',
            exit_code=0,
            )

    def test_053_regexp_BRE(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[["""s/ab??/cd/"""]],
            inputs=[[
"""ab??
"""]],
            stdout=(
"""cd
"""),
            stderr='',
            exit_code=0,
            )

    def test_054_regexp_BRE(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[["""s/ab+\\?/cd/"""]],
            inputs=[[
"""ab+?
"""]],
            stdout=(
"""cd?
"""),
            stderr='',
            exit_code=0,
            )

    def test_055_regexp_BRE(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[["""s/ab?\\?/cd/"""]],
            inputs=[[
"""ab??
"""]],
            stdout=(
"""cd?
"""),
            stderr='',
            exit_code=0,
            )

    def test_056_regexp_n(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#nr
/ab{1}c/p
/ab{2}c/p
/ab{3}c/p
"""]],
            inputs=[[
"""ac
abc
abbc
abbbc
abbbbc
"""]],
            stdout=(
"""abc
abbc
abbbc
"""),
            stderr='',
            exit_code=0,
            )

    def test_057_regexp_m_n(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#nr
/ab{2,3}c/p
"""]],
            inputs=[[
"""ac
abc
abbc
abbbc
abbbbc
"""]],
            stdout=(
"""abbc
abbbc
"""),
            stderr='',
            exit_code=0,
            )

    def test_058_regexp_n(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#nr
/ab{1,}c/p
/ab{2,}c/p
"""]],
            inputs=[[
"""ac
abc
abbc
abbbc
"""]],
            stdout=(
"""abc
abbc
abbc
abbbc
abbbc
"""),
            stderr='',
            exit_code=0,
            )

    def test_059_regexp_n(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#nr
/ab{,1}c/p
/ab{,2}c/p
"""]],
            inputs=[[
"""ac
abc
abbc
abbbc
"""]],
            stdout=(
"""ac
ac
abc
abc
abbc
"""),
            stderr='',
            exit_code=0,
            )

    def test_060_regexp_BRE_multiple_quantifier(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[["""s/ab**/cd/"""]],
            inputs=[[
"""abbb
"""]],
            stdout='',
            stderr=(
'sed.py error: -e #1 line 1 char 2: Invalid regex /ab**/ \
(translated to """(?s)ab**"""): multiple repeat\n'
if PY2 else
'sed.py error: -e #1 line 1 char 2: Invalid regex /ab**/ \
(translated to """(?s)ab**"""): multiple repeat at position 7\n'),
            exit_code=1,
            )

    def test_061_regexp_ERE_multiple_quantifier(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[['#r', 's/ab**/cd/']],
            inputs=[[
"""abbb
"""]],
            stdout='',
            stderr=(
'sed.py error: -e #2 line 1 char 2: Invalid regex /ab**/ \
(translated to """(?s)ab**"""): multiple repeat\n'
if PY2 else
'sed.py error: -e #2 line 1 char 2: Invalid regex /ab**/ \
(translated to """(?s)ab**"""): multiple repeat at position 7\n'),
            exit_code=1,
            )

    def test_062_regexp_BRE_multiple_quantifier(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[["""s/ab*\\?/cd/"""]],
            inputs=[[
"""abb
"""]],
            stdout='',
            stderr='sed.py error: -e #1 line 1 char 7: Invalid regexp: *\?' +
                   ' is not allowed in sed compatible mode.\n',
            exit_code=1,
            )

    def test_063_regexp_ERE_multiple_quantifier(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[['#r', 's/ab*?/cd/']],
            inputs=[[
"""abbb
"""]],
            stdout='',
            stderr='sed.py error: -e #2 line 1 char 6: Invalid regexp: *?' +
                   ' is not allowed in sed compatible mode.\n',
            exit_code=1,
            )

    def test_064_regexp_closing_bracket_in_char_set(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#n
/a[]x]*b/p
"""]],
            inputs=[[
"""a]x]]xx]b
"""]],
            stdout=(
"""a]x]]xx]b
"""),
            stderr='',
            exit_code=0,
            )

    def test_065_regexp_closing_bracket_in_complement_char_set(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#n
/a[^]]b/p
"""]],
            inputs=[[
"""axb
"""]],
            stdout=(
"""axb
"""),
            stderr='',
            exit_code=0,
            )

    def test_066_regexp_t_n_in_char_set(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#n
/a[\\t]b/p
h
G
/b[\\n]a/p
"""]],
            inputs=[[
"""a	b
"""]],
            stdout=(
"""a	b
a	b
a	b
"""),
            stderr='',
            exit_code=0,
            )

    def test_067_regexp_back_reference_before_num_in_address(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#n
/\\(abc\\)\\10/p
"""]],
            inputs=[[
"""abcabc0
"""]],
            stdout=(
"""abcabc0
"""),
            stderr='',
            exit_code=0,
            )

    def test_068_regexp_extended_back_reference_before_num_in_address(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#nr
/(abc)\\10/p
"""]],
            inputs=[[
"""abcabc0
"""]],
            stdout=(
"""abcabc0
"""),
            stderr='',
            exit_code=0,
            )

    def test_069_regexp_extended_unmatched_groups_1(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#r
s/(a)|(b)/\\1\\2/
"""]],
            inputs=[[
"""a
"""]],
            stdout=(
"""a
"""),
            stderr='',
            exit_code=0,
            )

    def test_070_regexp_extended_unmatched_groups_2(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#r
s/(x)?/\\1/
"""]],
            inputs=[[
"""a
"""]],
            stdout=(
"""a
"""),
            stderr='',
            exit_code=0,
            )

    def test_071_avoid_python_extension_1(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[["""s/b(\\?#foo)c/xyz/"""]],
            inputs=[[
"""ab#foo)cd
"""]],
            stdout=(
"""axyzd
"""),
            stderr='',
            exit_code=0,
            )

    def test_072_avoid_python_extension_2(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[["""s/b\\(\\?#foo\\)c/xyz/"""]],
            inputs=[[
"""abcd
"""]],
            stdout='',
            stderr='sed.py error: -e #1 line 1 char 7: Invalid regexp: \(\?' +
                   ' is not allowed in sed compatible mode.\n',
            exit_code=1,
            )

    def test_073__b_a_2(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#r
/((^|b)a){2}/p
"""]],
            inputs=[[
"""aa
"""]],
            stdout=(
"""aa
"""),
            stderr='',
            exit_code=0,
            )

    def test_074__a_b_2(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#r
/(a(b|$)){2}/p
"""]],
            inputs=[[
"""aa
"""]],
            stdout=(
"""aa
"""),
            stderr='',
            exit_code=0,
            )

    def test_075__a_2(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#r
/(^a){2}/p
"""]],
            inputs=[[
"""aa
"""]],
            stdout=(
"""aa
"""),
            stderr='',
            exit_code=0,
            )

    def test_076__a_2(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#r
/(a$){2}/p
"""]],
            inputs=[[
"""aa
"""]],
            stdout=(
"""aa
"""),
            stderr='',
            exit_code=0,
            )

    def test_077__2(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#r
/(^){2}/p
"""]],
            inputs=[[
"""aa
"""]],
            stdout=(
"""aa
aa
"""),
            stderr='',
            exit_code=0,
            )

    def test_078__2(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#r
/($){2}/p
"""]],
            inputs=[[
"""aa
"""]],
            stdout=(
"""aa
aa
"""),
            stderr='',
            exit_code=0,
            )

    def test_079_substitution_replace_first_occurrence(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[["""s/abc/x&y/"""]],
            inputs=[[
"""abcabcabc
"""]],
            stdout=(
"""xabcyabcabc
"""),
            stderr='',
            exit_code=0,
            )

    def test_080_substitution_replace_second_occurrence(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[["""s/abc/x&y/2"""]],
            inputs=[[
"""abcabcabc
"""]],
            stdout=(
"""abcxabcyabc
"""),
            stderr='',
            exit_code=0,
            )

    def test_081_substitution_replace_all_occurrences(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[["""s/abc/x&y/g"""]],
            inputs=[[
"""abcabcabc
"""]],
            stdout=(
"""xabcyxabcyxabcy
"""),
            stderr='',
            exit_code=0,
            )

    def test_082_substitution_replace_far_occurrence(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[["""s/abc/x&y/12"""]],
            inputs=[[
"""abcabcabcabcabcabcabcabcabcabcabcabc
"""]],
            stdout=(
"""abcabcabcabcabcabcabcabcabcabcabcxabcy
"""),
            stderr='',
            exit_code=0,
            )

    def test_083_substitution_occurrence_not_found(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[["""s/abc/x&y/12"""]],
            inputs=[[
"""abcabcabcabc
"""]],
            stdout=(
"""abcabcabcabc
"""),
            stderr='',
            exit_code=0,
            )

    def test_084_substitution_replace_all_occurrences_with_ignore_case_s_i(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[["""s/ABC/x&y/gi"""]],
            inputs=[[
"""abcabcabc
"""]],
            stdout=(
"""xabcyxabcyxabcy
"""),
            stderr='',
            exit_code=0,
            )

    def test_085_substitution_replace_all_occurrences_with_ignore_case_s_I(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[["""s/ABC/x&y/gI"""]],
            inputs=[[
"""abcabcabc
"""]],
            stdout=(
"""xabcyxabcyxabcy
"""),
            stderr='',
            exit_code=0,
            )

    def test_086_substitution_ignore_case_by_default(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[["""s/ABC/x&y/g"""]],
            inputs=[[
"""abcabcabc
"""]],
            stdout=(
"""abcabcabc
"""),
            stderr='',
            exit_code=0,
            )

    def test_087_substitution_back_reference_before_num_in_regexp(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[["""s/\\(abc\\)\\10/\\1/"""]],
            inputs=[[
"""abcabc0
"""]],
            stdout=(
"""abc
"""),
            stderr='',
            exit_code=0,
            )

    def test_088_substitution_back_reference_before_num_in_repl(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[["""s/\\(abc\\)/\\10/"""]],
            inputs=[[
"""abc
"""]],
            stdout=(
"""abc0
"""),
            stderr='',
            exit_code=0,
            )

    def test_089_substitution_r_back_reference_before_num_in_regexp(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#r
s/(abc)\\10/\\1/
"""]],
            inputs=[[
"""abcabc0
"""]],
            stdout=(
"""abc
"""),
            stderr='',
            exit_code=0,
            )

    def test_090_substitution_r_back_reference_before_num_in_repl(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#r
s/(abc)/\\10/
"""]],
            inputs=[[
"""abc
"""]],
            stdout=(
"""abc0
"""),
            stderr='',
            exit_code=0,
            )

    def test_091_substitution_empty_back_reference_in_regexp(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[["""s/abc\\(X\\{0,1\\}\\)abc\\1/&/"""]],
            inputs=[[
"""abcabc
"""]],
            stdout=(
"""abcabc
"""),
            stderr='',
            exit_code=0,
            )

    def test_092_substitution_in_replacement(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#nr
h; s/.*/&/; p
g; s/.*/&&&&/; p
"""]],
            inputs=[[
"""ha
"""]],
            stdout=(
"""ha
hahahaha
"""),
            stderr='',
            exit_code=0,
            )

    def test_093_substitution_new_line_in_replacement_old_style(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""s/ab/&\\
/g
"""]],
            inputs=[[
"""abcabc
"""]],
            stdout=(
"""ab
cab
c
"""),
            stderr='',
            exit_code=0,
            )

    def test_094_substitution_new_line_in_replacement_new_style(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[["""s/ab/&\\n/g"""]],
            inputs=[[
"""abcabc
"""]],
            stdout=(
"""ab
cab
c
"""),
            stderr='',
            exit_code=0,
            )

    def test_095_empty_regexp(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""# Check that the empty regex recalls the last *executed* regex,
# not the last *compiled* regex (from GNU sed test suite)
p
s/e/X/p
:x
s//Y/p
/f/bx
"""]],
            inputs=[[
"""eeefff
"""]],
            stdout=(
"""eeefff
Xeefff
XYefff
XYeYff
XYeYYf
XYeYYY
XYeYYY
"""),
            stderr='',
            exit_code=0,
            )

    def test_096_empty_regexp_empty_cascade(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""p
s/e/X/p
s//X/p
s//X/p
//s//X/p
"""]],
            inputs=[[
"""eeefff
"""]],
            stdout=(
"""eeefff
Xeefff
XXefff
XXXfff
XXXfff
"""),
            stderr='',
            exit_code=0,
            )

    def test_097_empty_regexp_case_modifier_propagation(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""p
s/E/X/igp
y/X/e/
s//X/p
"""]],
            inputs=[[
"""eeefff
"""]],
            stdout=(
"""eeefff
XXXfff
Xeefff
Xeefff
"""),
            stderr='',
            exit_code=0,
            )

    def test_098_empty_regexp_same_empty_regexp_different_case_status(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""p
s/E/X/ip
:a
s//X/p
s/E/X/p
ta
"""]],
            inputs=[[
"""eeeEEE
"""]],
            stdout=(
"""eeeEEE
XeeEEE
XXeEEE
XXeXEE
XXeXXE
XXeXXX
XXeXXX
"""),
            stderr='',
            exit_code=0,
            )

    def test_099_empty_regexp_case_modifier_propagation_for_addresses(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""/A/Ip
//p
"""]],
            inputs=[[
"""a
"""]],
            stdout=(
"""a
a
a
"""),
            stderr='',
            exit_code=0,
            )

    def test_100_branch_on_subst(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""s/abc/xy/
ta
s/$/foo/
:a
s/abc/xy/
tb
s/$/bar/
:b
"""]],
            inputs=[[
"""abc
"""]],
            stdout=(
"""xybar
"""),
            stderr='',
            exit_code=0,
            )

    def test_101_branch_on_one_successful_subst(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""s/abc/xy/
s/abc/xy/
ta
s/$/foo/
:a
"""]],
            inputs=[[
"""abc
"""]],
            stdout=(
"""xy
"""),
            stderr='',
            exit_code=0,
            )

    def test_102_branch_or_print_on_successful_subst_not_on_change_of_PS(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""s/abc/abc/p
s/abc/abc/
ta
s/$/foo/
:a
"""]],
            inputs=[[
"""abc
"""]],
            stdout=(
"""abc
abc
"""),
            stderr='',
            exit_code=0,
            )

    def test_103_Change_command_c(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""2c\\
two\\
deux
4,6c\\
quatre\\
cinq\\
six
8,9{ c\\
ocho\\
nueve
}
11 { a\\
eleven second
c\\
eleven first
}
i\\
not changed:
"""]],
            inputs=[[
"""1
2
3
4
5
6
7
8
9
10
11
12
"""]],
            stdout=(
"""not changed:
1
two
deux
not changed:
3
quatre
cinq
six
not changed:
7
ocho
nueve
ocho
nueve
not changed:
10
eleven first
eleven second
not changed:
12
"""),
            stderr='',
            exit_code=0,
            )

    def test_104_a_i_c(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""/TAG/ {
a\\
After
i\\
Before
c\\
Changed
}
"""]],
            inputs=[[
"""1
TAG
2
"""]],
            stdout=(
"""1
Before
Changed
After
2
"""),
            stderr='',
            exit_code=0,
            )

    def test_105_a_i_c_silent_mode(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#n
/TAG/ {
a\\
After
i\\
Before
c\\
Changed
}
"""]],
            inputs=[[
"""1
TAG
2
"""]],
            stdout=(
"""Before
Changed
After
"""),
            stderr='',
            exit_code=0,
            )

    def test_106_a_i_c_one_liners(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""/TAG/ {
a After
i Before
c Changed
}
"""]],
            inputs=[[
"""1
TAG
2
"""]],
            stdout=(
"""1
Before
Changed
After
2
"""),
            stderr='',
            exit_code=0,
            )

    def test_107_a_i_c_one_liners_ignore_leading_spaces(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""/TAG/ {
a     After
i        Before
c           Changed
}
"""]],
            inputs=[[
"""1
TAG
2
"""]],
            stdout=(
"""1
Before
Changed
After
2
"""),
            stderr='',
            exit_code=0,
            )

    def test_108_a_i_c_one_liners_include_leading_spaces_with(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""/TAG/ {
a \\    After
i \\       Before
c \\          Changed
}
"""]],
            inputs=[[
"""1
TAG
2
"""]],
            stdout=(
"""1
       Before
          Changed
    After
2
"""),
            stderr='',
            exit_code=0,
            )

    def test_109_a_i_c_one_liners_embedded_n(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""/TAG/ {
a Aft\\ner
i Bef\\nore
c Ch\\nang\\ned
}
"""]],
            inputs=[[
"""1
TAG
2
"""]],
            stdout=(
"""1
Bef
ore
Ch
ang
ed
Aft
er
2
"""),
            stderr='',
            exit_code=0,
            )

    def test_110_y_basic_usage(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#n
h
g; y/a/A/; p
g; y/abc/AAA/; p
g; y/abc/bca/; p
"""]],
            inputs=[[
"""abc
"""]],
            stdout=(
"""Abc
AAA
bca
"""),
            stderr='',
            exit_code=0,
            )

    def test_111_y_slashes(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#n
h
g; y/ABCD/xyzt/; p
g; y,ABCD,xyzt,; p
g; y/\\\\/X/; p
g; y/\\//X/; p
g; y,\\,,V,; p
g; y/\\A\\B\\C\\D/xyzt/; p
"""]],
            inputs=[[
"""A/B\\C,D
"""]],
            stdout=(
"""x/y\\z,t
x/y\\z,t
A/BXC,D
AXB\\C,D
A/B\\CVD
x/y\\z,t
"""),
            stderr='',
            exit_code=0,
            )

    def test_112_y_more_slashes_n_t(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#n
h
g; y/	/T/; p
g; y/\\t/T/; p
g; y/N/\\n/; p
g; y/N/\\
/; p
"""]],
            inputs=[[
"""a	bNc
"""]],
            stdout=(
"""aTbNc
aTbNc
a	b
c
a	b
c
"""),
            stderr='',
            exit_code=0,
            )

    def test_113_y_separators_including_t_space(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#n
h
g; ya\\aaAa; p
g; y b B ; p
g; y	c	C	; p
"""]],
            inputs=[[
"""abcd
"""]],
            stdout=(
"""Abcd
aBcd
abCd
"""),
            stderr='',
            exit_code=0,
            )

    def test_114_y_exceptions_not_delimited(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[["""y/ab/ab"""]],
            inputs=[[
"""abc
"""]],
            stdout='',
            stderr='sed.py error: -e #1 line 1 char 9: Missing delimiter /' +
                   ' for right parameter to command y\n',
            exit_code=1,
            )

    def test_115_y_exceptions_unequal_length(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[["""y/ab/abc/"""]],
            inputs=[[
"""abc
"""]],
            stdout='',
            stderr='sed.py error: -e #1 line 1 char 1: Left and right' +
                   ' arguments to command y must be of equal length.\n',
            exit_code=1,
            )

    def test_116_y_exceptions_additional_text(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[["""y/ab/ba/ and more"""]],
            inputs=[[
"""abc
"""]],
            stdout='',
            stderr='sed.py error: -e #1 line 1 char 10: Invalid extra characters after command y\n',
            exit_code=1,
            )

    def test_117_n_command_with_auto_print(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[["""n; p;"""]],
            inputs=[[
"""1
2
3
4
5
"""]],
            stdout=(
"""1
2
2
3
4
4
5
"""),
            stderr='',
            exit_code=0,
            )

    def test_118_n_command_without_auto_print(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#n
n; p;
"""]],
            inputs=[[
"""1
2
3
4
5
"""]],
            stdout=(
"""2
4
"""),
            stderr='',
            exit_code=0,
            )

    def test_119_N_command_with_auto_print(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[["""N; p;"""]],
            inputs=[[
"""1
2
3
4
5
"""]],
            stdout=(
"""1
2
1
2
3
4
3
4
5
"""),
            stderr='',
            exit_code=0,
            )

    def test_120_N_command_without_auto_print(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#n
N; p;
"""]],
            inputs=[[
"""1
2
3
4
5
"""]],
            stdout=(
"""1
2
3
4
"""),
            stderr='',
            exit_code=0,
            )

    def test_121_p_command_with_auto_print(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[["""p"""]],
            inputs=[[
"""1
2
3
"""]],
            stdout=(
"""1
1
2
2
3
3
"""),
            stderr='',
            exit_code=0,
            )

    def test_122_p_command_without_auto_print(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#n
p
"""]],
            inputs=[[
"""1
2
3
"""]],
            stdout=(
"""1
2
3
"""),
            stderr='',
            exit_code=0,
            )

    def test_123_P_command_with_auto_print(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[["""N; P;"""]],
            inputs=[[
"""1
2
3
4
5
"""]],
            stdout=(
"""1
1
2
3
3
4
5
"""),
            stderr='',
            exit_code=0,
            )

    def test_124_P_command_without_auto_print(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""#n
N; P;
"""]],
            inputs=[[
"""1
2
3
4
5
"""]],
            stdout=(
"""1
3
"""),
            stderr='',
            exit_code=0,
            )

    def test_125_v_command_earlier_and_no_version(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""v 4.5.3
v
"""]],
            inputs=[[
"""test data
"""]],
            stdout=(
"""test data
"""),
            stderr='',
            exit_code=0,
            )

    def test_126_v_command_later_version(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[["""v 5.0.3"""]],
            inputs=[[
"""test data
"""]],
            stdout='',
            stderr='sed.py error: -e #1 line 1 char 1: Requested version 5.0.3' +
                   ' is above provided version 4.8.0\n',
            exit_code=1,
            )

    def test_127_v_command_with_syntax_error(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[["""v 4.lo-9"""]],
            inputs=[[
"""test data
"""]],
            stdout='',
            stderr='sed.py error: -e #1 line 1 char 1: Invalid version' +
                   ' specification 4.lo-9. Use a number like 4.8.0\n',
            exit_code=1,
            )

    def test_128_F_command(self):
        tempfile = self.create_tempfile(ENCODING, 'f-command.', '1\n2\n3\n')
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[["""2F"""]],
            inputs=[tempfile],
            stdout=(
"""1
{tmp}
2
3
""".format(tmp=tempfile)),
            stderr='',
            exit_code=0,
            )

    def test_129_command_D_and_script_as_target(self):
        self.run_test(  # noqa: E122
            debug=0,
            encoding=ENCODING,
            scripts=[],
            inputs=["1,3H;4{s/.*/text/;x;p;D;};b"],
            stdin=(
"""1
2
3
4
5
6
"""),
            stdout=(
"""1
2
3

1
2
3
text
5
6
"""),
            stderr='',
            exit_code=0)

    def test_130_separate(self):
        input_file_1 = self.create_tempfile(ENCODING, 'input_1.',
                                            'Line 1.1\nLine 1.2\nLine 1.3\nLine 1.4\n')
        input_file_2 = self.create_tempfile(ENCODING, 'input_2.',
                                            'Line 2.1\nLine 2.2\nLine 2.3\nLine 2.4\n')
        input_file_3 = self.create_tempfile(ENCODING, 'input_3.',
                                            'Line 3.1\nLine 3.2\nLine 3.3\nLine 3.4\n')
        input_file_4 = self.create_tempfile(ENCODING, 'input_4.',
                                            'Line 4.1\nLine 4.2\nLine 4.3\nLine 4.4\n')
        script_file = self.create_tempfile(ENCODING, 'script.', '1x\n$x\n')
        self.run_test(  # noqa: E122
            debug=0,
            encoding=ENCODING,
            options=['--separate'],
            scripts=[script_file],
            inputs=[input_file_1, input_file_2, input_file_3, input_file_4],
            stdout=(
"""\nLine 1.2\nLine 1.3\nLine 1.1
Line 1.4\nLine 2.2\nLine 2.3\nLine 2.1
Line 2.4\nLine 3.2\nLine 3.3\nLine 3.1
Line 3.4\nLine 4.2\nLine 4.3\nLine 4.1
"""),
            stderr='',
            exit_code=0)

    def test_131_version_output(self):
        self.run_test(  # noqa: E122
            debug=0,
            encoding=ENCODING,
            options=['-v'],
            scripts=[],
            inputs=[],
            stdin='',
            stdout='',
            stderr='\nsed.py - python sed module and command line utility\nVersion: 2.00\n',
            exit_code=0)

    def test_132_write_to_stdout_and_stderr(self):
        self.run_test(  # noqa: E122
            debug=0,
            encoding=ENCODING,
            scripts=[
["""#rn
0,/Line 1/w /dev/stdout
0~0,/Line 2/w /dev/stderr
3w -
"""]],
            inputs=[],
            stdin=(
"""Line 1
Line 2
Line 3
"""),
            stdout='Line 1\nLine 3\n',
            stderr='Line 1\nLine 2\n',
            exit_code=0)

    def test_133_write_output_to_file_and_command_T(self):
        tempfile_name = self.create_tempfile(ENCODING, 'output-test.', '')
        self.run_test(  # noqa: E122
            debug=0,
            encoding=ENCODING,
            python_syntax=True,
            scripts=[
["""#r
:loop
s/cats like to eat (\\w*)/\\1 like to eat wheat/
s/\\.\\Z/!/
T loop # this jump will never happen!
T # this branch to <end cycle> will always happen
"""]],
            inputs=[["""Many... cats like to eat mice."""]],
            redirect=tempfile_name,
            stdin='',
            stdout='',
            stderr='',
            output_files={tempfile_name: 'Many... mice like to eat wheat!'},
            exit_code=0)

    def test_134_write_output_to_named_file(self):
        tempfile_name = self.create_tempfile(ENCODING, 'output-test.', '')
        self.run_test(  # noqa: E122
            debug=0,
            encoding=ENCODING,
            python_syntax=True,
            scripts=[
["""#rn
s/cats like to eat (\\w*)/\\1 like to eat wheat/;P;t
"""]],
            inputs=[["""Many cats like to eat mice."""]],
            redirect=tempfile_name,
            stdin='',
            stdout='',
            stderr='',
            output_files={tempfile_name: 'Many mice like to eat wheat.'},
            exit_code=0)

    def test_135_encoding_script_and_input(self):
        self.run_test(  # noqa: E122
            debug=0,
            encoding=ENCODING,
            python_syntax=True,
            scripts=[
["""#r
s/ä/\\x61e/g
s/\\N{Latin Capital letter A with diaeresis}/Ae/g
s/\\u00FC/ue/g
s/Ü/Ue/g
s/ö/oe/g
s/\\U000000d6/Oe/g
s/ß/ss/g
"""]],
            inputs=[
["""Ähren ähneln üblen Übeltätern
Öfter mal örtliche Geschäfte besuchen
Straßenlaterne
"""]],
            stdin='',
            stdout=(
"""Aehren aehneln ueblen Uebeltaetern
Oefter mal oertliche Geschaefte besuchen
Strassenlaterne
"""),
            stderr='',
            exit_code=0)

    def test_136_collating_symbol(self):
        self.run_test(  # noqa: E122
            debug=0,
            encoding=ENCODING,
            scripts=[['#r', 's/([[.ch.]])/\\1/g']],
            inputs=[
["""ab,!
"""]],
            stdin='',
            stdout='',
            stderr='sed.py error: -e #2 line 1 char 5: The collating symbol specification ' +
            '[.ch.] is not supported by Python regular expressions.\n',
            exit_code=1)

    def test_137_equivalence_class(self):
        self.run_test(  # noqa: E122
            debug=0,
            encoding=ENCODING,
            scripts=[['#r', 's/([[=a=]])/\\1/g']],
            inputs=[
["""ab,!
"""]],
            stdin='',
            stdout='',
            stderr='sed.py error: -e #2 line 1 char 5: The equivalence class specification ' +
            '[=a=] is not supported by Python regular expressions.\n',
            exit_code=1)

    def test_138_character_class(self):
        self.run_test(  # noqa: E122
            debug=0,
            encoding=ENCODING,
            scripts=[['#r', 's/([[:lower:]])/\\U\\1/g']],
            inputs=[
["""ab,!
"""]],
            stdin='',
            stdout='',
            stderr='sed.py error: -e #2 line 1 char 5: The character class specification ' +
            '[:lower:] is not supported by Python regular expressions.\n',
            exit_code=1)

    def test_139_pythonsed_extension_command_z(self):
        tempfile_name = self.create_tempfile(ENCODING, 'command-z-input.',  # noqa: E122
"""a
b
c
d
e
""")
        self.run_test(  # noqa: E122
            debug=0,
            encoding=ENCODING,
            scripts=[
["""
2~0,4z # this will replace lines b,c and d with an empty line
$q
"""]],
            inputs=[tempfile_name],
            stdin='',
            stdout=(
"""a



e
"""),
            stderr='',
            exit_code=0)

    def test_140_read_non_existent_file_and_command_equal(self):
        self.run_test(  # noqa: E122
            debug=0,
            encoding=ENCODING,
            scripts=[
["""# next line: testing address range with count 0 as well
2,+0r i-do-not-exist.file
3=
4{} # testing empty block
"""]],
            inputs=[
["""a
b
c
d
"""]],
            stdin='',
            stdout='a\nb\n3\nc\nd\n',
            stderr='',
            exit_code=0)

    def test_141_write_file_from_s_command(self):
        write_file_1 = self.create_tempfile(ENCODING, 's-cmd-write.1.', '')
        write_file_2 = self.create_tempfile(ENCODING, 's-cmd-write.2.', '')
        self.run_test(  # noqa: E122
            debug=0,
            encoding=ENCODING,
            scripts=[
["""#r
N;N
s/(.)b(.)/\\1B\\1/mw {wrt1}
T skip
d
:skip
s/\\nb\\n/\\nBB\\n/mw {wrt2}
""".format(wrt1=write_file_1, wrt2=write_file_2)]],
            inputs=[
["""a
b
c
d
"""]],
            stdin='',
            stdout=(
"""a
BB
c
d
"""),
            stderr='',
            output_files={write_file_1: '', write_file_2: 'a\nBB\nc'},
            exit_code=0)

    def test_142_newline_as_delimiter(self):
        self.run_test(  # noqa: E122
            debug=0,
            encoding=ENCODING,
            scripts=[
["""
/a/I,~4 y
ab
BA
/b/M,+3{s
c
D
;s
d
C
Ig
}
s
e
E

h
"""]],
            inputs=[
["""bcde
bcde
bcde
bcde
bcde
abcd
bcde
bcde
bcde
bcde
"""]],
            stdin='',
            stdout=(
"""bCCE
bCCE
bCCE
bCCE
bCCE
BACC
ACCE
ACCE
bCCE
bCCE
"""),
            stderr='',
            exit_code=0)

    def test_143_command_z_and_separate(self):
        self.run_test(  # noqa: E122
            debug=0,
            separate=True,
            scripts=[
["""
2~3z
"""]],
            inputs=[
["""1
2
3
4
5
6
7
8
9
10
"""],
["""11
12
13
14
15
16
"""]],
            stdin='',
            stdout=(
"""1

3
4

6
7

9
10
11

13
14

16
"""),
            stderr='',
            exit_code=0)

    def test_144_command_w(self):
        write_file = self.create_tempfile(ENCODING, 'w-cmd-write.', '')
        self.run_test(  # noqa: E122
            debug=0,
            encoding=ENCODING,
            scripts=[
["""#n
N;N;N;p
w """+write_file]],
            inputs=[[
"""1
2
3
4
5
6
7
8
9
10
"""]],
            stdin='',
            stdout=(
"""1
2
3
4
5
6
7
8
"""),
            stderr='',
            output_files={write_file: '1\n2\n3\n4\n5\n6\n7\n8\n'},
            exit_code=0)

    def test_145_command_W(self):
        write_file = self.create_tempfile(ENCODING, 'W-cmd-write.', '')
        self.run_test(  # noqa: E122
            debug=0,
            encoding=ENCODING,
            scripts=[
["""#n
N;N;N;p
W """+write_file]],
            inputs=[[
"""1
2
3
4
5
6
7
8
9
10
"""]],
            stdin='',
            stdout=(
"""1
2
3
4
5
6
7
8
"""),
            stderr='',
            output_files={write_file: '1\n5\n'},
            exit_code=0)

    def test_146_command_r(self):
        tmp_file = self.create_tempfile(ENCODING, 'readfile-test.', """Line 1
Line 2
Line 3""")
        self.run_test(  # noqa: E122
            debug=0,
            encoding=ENCODING,
            scripts=[
["""3r {tmp}
5r {tmp}
""".format(tmp=tmp_file)]],
            inputs=[[
"""1
2
3
4
5
6
7
8
"""]],
            stdin='',
            stdout=(
"""1
2
3
Line 1
Line 2
Line 3
4
5
Line 1
Line 2
Line 3
6
7
8
"""),
            stderr='',
            exit_code=0)

    def test_147_command_R(self):
        tmp_file_1 = self.create_tempfile(ENCODING, 'readline-test-1.', """Line 1.1
Line 1.2
Line 1.3""")
        tmp_file_2 = self.create_tempfile(ENCODING, 'readline-test-2.', """Line 2.1
Line 2.2
Line 2.3""")
        self.run_test(  # noqa: E122
            debug=0,
            encoding=ENCODING,
            scripts=[
["""1R {tmp1}
2R {tmp2}
3R {tmp1}
5,~0R {tmp1}
5R -
7,6R {tmp1}
7R /dev/stdin
7R {tmp1}
7R i-do-not-exist.file
""".format(tmp1=tmp_file_1, tmp2=tmp_file_2)]],
            inputs=[[
"""1
2
3
4
5
6
7
8
"""]],
            stdin='One line from stdin\nAnother line from stdin',
            stdout=(
"""1
Line 1.1
2
Line 2.1
3
Line 1.2
4
5
Line 1.3
One line from stdin
6
7
Another line from stdin
8
"""),
            stderr='',
            exit_code=0)

    def test_148_python_syntax(self):
        self.run_test(  # noqa: E122
            debug=0,
            encoding=ENCODING,
            python_syntax=True,
            scripts=[
["""#n
1{
s/(?<=a)b(?!c)/\\N{Tilde}/g
s/^(.)(.)(.)(.)(.)(.)(.)(.)(.)(.)(.)(.)/\\12\\11\\10\\9\\8\\7\\6\\5\\4\\3\\2\\1\\075\\170\\241/
p
}
2,${N;l71;l}
"""]],
            inputs=[[
"""abcbdbeab-bc
Otto\0Emil\1Hugo\x09\vMake \a\fthis a little longer so it will span more than 70 characters\\.
and some more
"""]],
            stdin='',
            stdout=(
"""cb-~aebdbcba=x¡
Otto\\000Emil\\001Hugo\\t\\vMake \\a\\fthis a little longer so it will span \\
more than 70 characters\\\\.\\nand some more$
Otto\\000Emil\\001Hugo\\t\\vMake \\a\\fthis a little longer so it will span\\
 more than 70 characters\\\\.\\nand some more$
"""),
            stderr='',
            exit_code=0)

    def test_149_flipcase(self):
        self.run_test(  # noqa: E122
            debug=0,
            encoding=ENCODING,
            scripts=[
["""#nr
h
g; s/^[dD](.)[lL](.)[uU](.)[aA](.)$/asis:  \\E\\1 \\2\\l\\2\\2 \\3\\u\\3\\3 \\E\\4/p
g; s/^[dD](.)[lL](.)[uU](.)[aA](.)$/lower: \\U\\L\\1 \\2\\l\\2\\2 \\3\\u\\3\\3 \\E\\4/p
g; s/^[dD](.)[lL](.)[uU](.)[aA](.)$/upper: \\U\\1 \\2\\l\\2\\2 \\3\\u\\3\\3 \\E\\4/p
"""]],
            inputs=[[
"""ddlluuaa
DDLLUUAA
"""]],
            stdin='',
            stdout=(
"""asis:  d lll uUu a
lower: d lll uUu a
upper: D LlL UUU a
asis:  D LlL UUU A
lower: d lll uUu A
upper: D LlL UUU A
"""),
            stderr='',
            exit_code=0)

    @pytest.mark.skipif(sys.version_info < (3,0), reason="stash uses encoding='ascii' on stdout redirects under Python 2")
    def test_150_escapes(self):
        tempfile = self.create_tempfile(ENCODING, 'piped-stdout.', '')
        self.run_test(  # noqa: E122
            debug=0,
            encoding=ENCODING,
            scripts=[
["""#r
1 {
  s/\\a/\\\\-a-/g
  s/\\f/\\\\-f-/g
# s/\\r/\\\\-r-/g # \\r is interpreted as newline by stash
  s/\\t/\\\\-t-/g
  s/\\v/\\\\-v-/g
}
2 s:\\B:\\::g
# the l command will encode the pattern space to bytes using the given encoding before printing it!
# next 2 lines are creating uft-8 character from two bytes: \\xc2\\xa1 is inverted exclamation mark
3 { s/\\`.*(\\<..\\>).*\\´/\\0\\1\\cm\\cM\\d065\\o142\\x43\\,\\xc2\\xa1/;l;d }
4 s/a/\\xc2\\xa1/
"""]],
            inputs=[['\a\f\t\v', 'abc %-= def.', 'abc de fghi', 'a']],
            redirect=tempfile,
            stdin='',
            stdout='',
            output_files={ tempfile:
"""\\-a-\\-f-\\-t-\\-v-
a:b:c :%:-:=: d:e:f.:
\\000de\\r\\rAbC,\\302\\241$
¡
"""},
            stderr='',
            exit_code=0)

    def test_151_backslash_in_charlist(self):
        self.run_test(  # noqa: E122
            debug=0,
            encoding=ENCODING,
            scripts=[
["""
\\|[\\]|d
"""]],
            inputs=[['a\nb\nc\\\nd']],
            stdin='',
            stdout='a\nb\nd',
            stderr='',
            exit_code=0)

    def test_152_invalid_number_in_address(self):
        self.run_test(  # noqa: E122
            debug=0,
            encoding=ENCODING,
            scripts=[['1~a p']],
            inputs=[['a']],
            stdin='',
            stdout='',
            stderr='sed.py error: -e #1 line 1 char 3: Expected number\n',
            exit_code=1)

    def test_153_cmd_l_invalid_number(self):
        self.run_test(  # noqa: E122
            debug=0,
            encoding=ENCODING,
            scripts=[['l abc']],
            inputs=[['a']],
            stdin='',
            stdout='',
            stderr='sed.py error: -e #1 line 1 char 3: Only an integer number ' + \
            'can follow command l as parameter',
            exit_code=1)

    def test_154_address_without_command(self):
        self.run_test(  # noqa: E122
            debug=0,
            encoding=ENCODING,
            scripts=[['/hugo/', 'p']],
            inputs=[['a']],
            stdin='',
            stdout='',
            stderr='sed.py error: -e #1 line 1 char 1: Address without a command\n',
            exit_code=1)

    def test_155_undefined_lables(self):
        self.run_test(  # noqa: E122
            debug=0,
            encoding=ENCODING,
            scripts=[[': defined',
                      'b undefined1',
                      ' t undefined2',
                      'T undefined1']],
            inputs=[['a']],
            stdin='',
            stdout='',
            stderr=['sed.py error: Undefined labels referenced:\n',
                    '    undefined1 at -e #2 line 1 char 1\n',
                    '    undefined1 at -e #4 line 1 char 1\n',
                    '    undefined2 at -e #3 line 1 char 2\n'],
            exit_code=1)

    def test_156_unclosed_blocks(self):
        self.run_test(  # noqa: E122
            debug=0,
            encoding=ENCODING,
            scripts=[['${', '# unclosed block 1', '/a/{ # unclosed block 2', 'Q']],
            inputs=[['a']],
            stdin='',
            stdout='',
            stderr=('sed.py error: Unclosed blocks starting at -e #1 line 1 char 2,' +
                    ' -e #3 line 1 char 4'),
            exit_code=1)

    def test_157_script_ends_with_continuation(self):
        self.run_test(
            debug=0,
            encoding=ENCODING,
            scripts=[['p', 'i\\']],
            inputs=[['a']],
            stdin='',
            stdout='',
            stderr='sed.py error: -e #2 line 1: Invalid line continuation on last script line\n',
            exit_code=1)

    def test_158_script_file_not_found(self):
        self.run_test(
            debug=0,
            encoding=ENCODING,
            scripts=['some-file-that-does-not-exist.sed'],
            inputs=[['a']],
            stdin='',
            stdout='',
            stderr='sed.py error: Script file some-file-that-does-not-exist.sed does not exist.\n',
            exit_code=1)

    def test_159_no_script(self):
        self.run_test(
            debug=0,
            encoding=ENCODING,
            scripts=[[' # some empty script', ' # just comments']],
            inputs=[['a']],
            stdin='',
            stdout='',
            stderr='sed.py error: Empty script specified.\n',
            exit_code=1)

    def test_160_no_script(self):
        self.run_test(
            debug=0,
            encoding=ENCODING,
            scripts=[],
            inputs=[],
            stdin='',
            stdout=None,
            stderr='sed.py error: No script specified.\n',
            exit_code=1)

    # This testcase does not make sense in stash, since all tests are going through main
    # and in this case, the input file name generated by run_test would
    # be taken as script and producing 'unknown command' errors.
    # def test_161_no_script(self):
    #    self.run_test(
    #        debug=0,
    #        encoding=ENCODING,
    #        scripts=[],
    #        inputs=[['a']],
    #        stdin='',
    #        stdout='',
    #        stderr='sed.py error: No script specified.\n',
    #        exit_code=1)

    def test_162_inplace_editing_move(self):

        input_data = """this is text
to be edited
inplace, to test that feature.
"""
        expected_content = """this is text
to be edited and checked
afterwards for a test of in-place editing.
"""
        script = """3s/edited/& and checked/
$c afterwards for a test of in-place editing.
"""
        input_file_1 = self.create_tempfile(ENCODING, 'input_1.', 'input_1\n'+input_data)
        input_file_2 = self.create_tempfile(ENCODING, 'input_2.', 'input_2\n'+input_data)
        self.run_test(
            debug=0,
            in_place='/tmp/*',
            scripts=[[script]],
            inputs=[input_file_1, input_file_2],
            stdout='',
            stderr='',
            inplace_content=['input_1\n'+expected_content,
                             'input_2\n'+expected_content])

    def test_163_inplace_editing_prefix(self):

        input_data = """this is text
to be edited
inplace, to test that feature.
"""
        expected_content = """this is text
to be edited and checked
afterwards for a test of in-place editing.
"""
        script = """3s/edited/& and checked/
4c afterwards for a test of in-place editing.
"""
        input_file_1 = self.create_tempfile(ENCODING, 'input_1.', 'input_1\n'+input_data)
        input_file_2 = self.create_tempfile(ENCODING, 'input_2.', 'input_2\n'+input_data)
        self.run_test(
            debug=0,
            in_place='backup-*',
            scripts=[[script]],
            inputs=[input_file_1, input_file_2],
            stdout='',
            stderr='',
            inplace_content=['input_1\n'+expected_content,
                             'input_2\n'+expected_content])

    def test_164_inplace_editing_suffix(self):

        input_data = """this is text
to be edited
inplace, to test that feature.
"""
        expected_content = """this is text
to be edited and checked
afterwards for a test of in-place editing.
"""
        script = """3s/edited/& and checked/
4c afterwards for a test of in-place editing.
"""
        input_file_1 = self.create_tempfile(ENCODING, 'input_1.', 'input_1\n'+input_data)
        input_file_2 = self.create_tempfile(ENCODING, 'input_2.', 'input_2\n'+input_data)
        self.run_test(
            debug=0,
            in_place='.bkup',
            scripts=[[script]],
            inputs=[input_file_1, input_file_2],
            stdout='',
            stderr='',
            inplace_content=['input_1\n'+expected_content,
                             'input_2\n'+expected_content])

    def test_165_inplace_editing_no_backup_single_file(self):

        input_data = """this is text
to be edited
inplace, to test that feature.
"""
        expected_content = """this is text
to be edited and checked
afterwards for a test of in-place editing.
"""
        input_file_1 = self.create_tempfile(ENCODING, 'input_1.', 'input_1\n'+input_data)
        self.run_test(
            debug=0,
            in_place='',
            scripts=[['3s/edited/& and checked/',
                      '4c afterwards for a test of in-place editing.']],
            inputs=[input_file_1],
            stdout='',
            stderr='',
            inplace_content=['input_1\n'+expected_content],
            exit_code=0)

    def test_166_inplace_editing_no_backup(self):

        input_data = """this is text
to be edited
inplace, to test that feature.
"""
        expected_content = """this is text
to be edited and checked
afterwards for a test of in-place editing.
"""
        script = """3s/edited/& and checked/
4c afterwards for a test of in-place editing.
"""
        input_file_1 = self.create_tempfile(ENCODING, 'input_1.', 'input_1\n'+input_data)
        input_file_2 = self.create_tempfile(ENCODING, 'input_2.', 'input_2\n'+input_data)
        self.run_test(
            debug=0,
            in_place='',
            scripts=[[script]],
            inputs=[input_file_1, input_file_2],
            stdout='',
            stderr='',
            inplace_content=['input_1\n'+expected_content,
                             'input_2\n'+expected_content],
            exit_code=0)

    def test_167_add_script_and_data_all_ways_and_test_line_continuation_on_last_line(self):
        script_file_name = self.create_tempfile(ENCODING, 'script_file_test.', '2p \\')
        script_stream = StringIO('\\!3!,-\\!4!p')
        # last script line is with dangling continuation!!
        script_file = self.create_tempfile(ENCODING, 'script_open_file_test.', '1,-$!p \\')
        input_file_name = self.create_tempfile(ENCODING, 'input_file_test.', 'Line 2')
        input_stream = StringIO('Line 3')
        input_file = self.create_tempfile(ENCODING, 'input_open_file_test.', 'Line 4')
        with open(script_file, 'rt', encoding=ENCODING) as script_file_open, \
             open(input_file, 'rt', encoding=ENCODING) as input_file_open:  # noqa: E127
            self.run_test(  # noqa: E122
                debug=0,
                encoding=ENCODING,
                no_autoprint=False,
                scripts=[
['1p'],
script_file_name,
script_stream,
script_file_open,
['$Q 10']
],
                inputs=[
['Line 1'],
input_file_name,
input_stream,
input_file_open
],
                stdout=(
"""Line 1
Line 1
Line 2
Line 2
Line 3
Line 3
Line 4"""),
                stderr='',
                exit_code=10)

    def test_168_comment_syntax_and_data_from_stdin_via_inputs_1(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""1 p # comment
2 s/abc/&&/ # comments can not continue across lines \\
p
"""]],
            inputs=['-'],
            stdin=(
"""abc1
abc2
"""),                     # input string fed to sed through stdin
            stdout=(
"""abc1
abc1
abc1
abcabc2
abcabc2
"""),
            stderr='',
            exit_code=0,
            )

    def test_169_comment_syntax_and_data_from_stdin(self):
        self.run_test(  # noqa: E122
            debug=0,
            scripts=[[
"""1 p # comment
2 s/abc/&&/ # comments can not continue across lines \\
p
"""]],
            stdin=(
"""abc1
abc2
"""),                     # input string fed to sed through stdin
            stdout=(
"""abc1
abc1
abc1
abcabc2
abcabc2
"""),
            stderr='',
            exit_code=0,
            )

    def test_170_debug_mode_3(self):
        self.run_test(  # noqa: E122
            debug=3,
            scripts=[[
"""1 { s/\\x5c//; p }
2 { s/abc/&&/
    i an extra line
    i \\
    and one with leading spaces\\
and one without
  }
"""]],
            inputs=[[
"""ab\\c1
abc2
"""]],
            stdout=(
"""abc1
abc1
an extra line
    and one with leading spaces
and one without
abcabc2
"""),
            stderr=None,  # we do not check the debug output!!!
            exit_code=0,
            )
