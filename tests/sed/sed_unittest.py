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

from stash.tests.stashtest import StashTestCase


DEFAULT_ENCODING = locale.getpreferredencoding()
PY2 = sys.version_info[0] == 2
if PY2:

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
    """A test case implementing utility methods for testing PythonSed"""

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

    def run_test_against_object(self, **kwargs):
        self.run_test_against_main(**kwargs)

    def run_test_against_main(
            self,
            debug=0,              # debug level (0..3)
            encoding=DEFAULT_ENCODING,   # input encoding
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
        args = ['sed.py', '--encoding='+encoding]
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

