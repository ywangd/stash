# -*- coding: utf-8 -*-
"""Search a regular expression pattern in one or more files"""

from __future__ import print_function

import os
import io
import re
import sys
import argparse
import fnmatch

_stash = globals()['_stash']


class Path(object):
    def __init__(self,pathname):
        self.pathname = pathname
        self.real_pathname = os.path.realpath(pathname)
        
    def __str__(self):
        return self.pathname
    
    def pretty(self):
        return _stash.libcore.abbreviate(self.pathname)
    
    def is_file(self):
        return os.path.isfile(self.real_pathname)
    
    def is_dir(self):
        return os.path.isdir(self.real_pathname)
    
    def exists(self):
        return os.path.exists(self.pathname)
    
    @property
    def parent(self):
        return Path(os.path.dirname(self.pathname))
    
    @property 
    def name(self):
        return os.path.basename(self.pathname)
    
    def rglob(self,pattern):
        """ returns an iterable through all files
            matching the specified pattern in this
            directory (self.pathname must denote
            a directory - and the caller is taking
            care of this in this script therefore
            no check is necessary here)
        """
        for root,_,files in os.walk(self.pathname):
            for fn in fnmatch.filter(files,pattern):
                yield Path(os.path.join(root,fn))


class CountOutputHandler(object):
    """ An object of this class keeps track on the count
        of matches for the file currently being processed.
        through the method new_file it is informed whenever
        processing of a new file is started.
        It also provides a "pretty" name (filename_to_print)
        to be used in the printed output of the grep command.
    """
    def __init__(self,files_without_match=False,
                      files_with_matches=False,
                      no_filename=False,
                      count_only=False):
        self.files_without_match = files_without_match
        self.files_with_matches = files_with_matches
        self.no_filename = no_filename
        self.count_only = count_only
        self.count = 0
        self.filename_to_print = None
        
    def new_file(self,filename_to_print):
        if self.filename_to_print:
            self.print_on_count()
        self.count = 0
        self.filename_to_print = filename_to_print

    def count_match(self):
        self.count += 1
        
    def print_on_count(self):
        """ If either the --count or --files-without-match option is
            active, this method takes care of creating the necessary
            output after a file finished processing.
            Otherwise it does nothing.
        """
        if self.count_only:
            if self.no_filename:
                print(str(self.count))
            else:
                print(u'{fn}:{cnt}'
                      .format(cnt=self.count,fn=self.filename_to_print))
        if self.files_without_match and self.count==0:
            print(self.filename_to_print)
        elif self.files_with_matches and self.count>0:
            print(self.filename_to_print)


class FileInputHandler(object):
    """ This class provides input lines from a series
        of files opening and closing them as needed.
        Also for every new file opened a callback is
        used to signal the change of the input file.
    """
    def __init__(self,filepaths,
                      new_file_callback,
                      stdin_label='<stdin>',
                      encoding='latin1'):

        self.filepaths = filepaths
        self.new_file_callback = new_file_callback
        self.stdin_label = stdin_label
        self.encoding = encoding
        self.lineno = 0
        
        self.keep_reading_file = True
        
    def nextfile(self):
        """ This method is called to signal, that the 
            rest of the file currently being read is
            to be skipped.
        """
        self.keep_reading_file = False
                    
    def input(self):
        """ This method is an iterator over all the lines of
            the combined input files passed in, when this
            object was created.
            Calls to nextfile() can have the rest of the current
            file being skipped.
        """
        while len(self.filepaths)>0:
            filepath = self.filepaths.pop(0)
            if filepath:
                self.new_file_callback(str(filepath))
                filehndl = io.open(str(filepath),mode='rt',encoding=self.encoding)
            else:
                self.new_file_callback(self.stdin_label)
                filehndl = sys.stdin

            self.keep_reading_file = True
            self.lineno = 1
            line = filehndl.readline()
            while len(line)>0 and self.keep_reading_file:
                yield line
                self.lineno += 1
                line = filehndl.readline()
 
            if filehndl!=sys.stdin:
                filehndl.close()
                
        self.new_file_callback(None) # signal callback we are done
    
def main(args):
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument('--help', action='help', help='show this help message and exit')
    ap.add_argument('pattern', help='the pattern to match')
    ap.add_argument('files', nargs='*', help='files to be searched')
    ap.add_argument('-i', '--ignore-case', action='store_true', help='ignore case while searching')
    ap.add_argument('-v', '--invert', action='store_true', help='invert the search result')
    ap.add_argument('-r', '--recursive', action='store_true', help='search directories recursively for matching files')
    ap.add_argument('-n', '--line-number', action='store_true', help='prefix each line with the line number')
    ap.add_argument('-H', '--with-filename', action='store_true', help='prefix each line with the file name (default if multiple files are searched)')
    ap.add_argument('-h', '--no-filename', action='store_true', help='do not prefix each line with the file name (default if stdin or a single file is searched)')
    ap.add_argument('--label', action='store', default='<stdin>', help='label to use as file name for stdin')
    ap.add_argument('-c', '--count', action='store_true', help='count the search results instead of normal output')
    ap.add_argument('-L','--files-without-match', action='store_true', help='only list file names of files that do not match')
    ap.add_argument('-l','--files-with-matches', action='store_true', help='only list file names of files that match')
    ap.add_argument('-o','--only-matching', action='store_true', help='only print the matching parts')
    ap.add_argument('--color', action='store_true', help='color matched text in output')
    ap.add_argument('--encoding', action='store', default='latin1',help='encoding to use when opening files (default encoding is latin1)')

    rc = 1 # 1 (no match found) is the default return code
    try:
        ns = ap.parse_args(args)
    
        flags = 0
        if ns.ignore_case:
            flags |= re.IGNORECASE
    
        pattern = re.compile(ns.pattern, flags=flags)
    
        filepaths = []
        if ns.recursive:
            for f in ns.files:
                if f=="-":
                    filepaths.append(None)
                else:
                    p = Path(f)
                    if p.is_dir():
                        filepaths += p.rglob('*')
                    else:
                        d = p.parent
                        n = p.name
                        filepaths += d.rglob(n)
        elif len(ns.files)==0:
            filepaths.append(None)
        else:
            # Do not try to grep directories
            for f in ns.files:
                if f=="-":
                    filepaths.append(None)
                else:
                    p = Path(f)
                    if p.is_file():
                        filepaths.append(p)
                    elif not p.exists():
                        print('grep: {} was skipped because it does not exist.'.format(f),file=sys.stderr)
                    else:
                        print('grep: {} was skipped because it is not a file.'.format(f),file=sys.stderr)
            if len(filepaths)==0:
                print('grep: No valid files given. Exiting.',file=sys.stderr)
                return 1
                    
    
        no_filename = (len(filepaths)<=1)
        if ns.no_filename:
            no_filename = True
            if ns.with_filename:
                print('grep: option --with-filename ignored since --no-filename was specified as well.',file=sys.stderr)
        elif ns.with_filename:
            no_filename = False
            
        if no_filename:
            if ns.line_number:
                fmt = u'{lineno}:{line}'
            else:
                fmt = u'{line}'
        elif ns.line_number:
            fmt = u'{filename}:{lineno}:{line}'
        else:
            fmt = u'{filename}:{line}'
    
        count_output_handler = CountOutputHandler(ns.files_without_match,
                                                  ns.files_with_matches,
                                                  no_filename,
                                                  ns.count)
        file_input_handler = FileInputHandler(filepaths, count_output_handler.new_file, ns.label, ns.encoding)

        for line in file_input_handler.input():
            if bool(pattern.search(line))!=ns.invert:
                rc = 0 # we had a match, therefore we will have return code 0
                count_output_handler.count_match()
                if ns.files_with_matches:
                    if not ns.invert and not ns.count: # if we do not need a count, skip the rest of the file
                        file_input_handler.nextfile()
                elif not (ns.count or
                          ns.files_without_match):
                    if ns.invert:
                        # optimize: no match, so no highlight color needed
                        lines = [ line ]
                    elif ns.only_matching:
                        if ns.color:
                            lines = [ _stash.text_color(m.group(), 'red')+'\n' for m in pattern.finditer(line) ]
                        else:
                            lines = [ m.group()+'\n' for m in pattern.finditer(line) ]
                    elif ns.color:
                        lines = [ re.sub(pattern, lambda m: _stash.text_color(m.group(), 'red'), line) ]
                    else:
                        lines = [ line ]
                    
                    for ln in lines:
                        print(fmt.format(filename=count_output_handler.filename_to_print,
                                         lineno=file_input_handler.lineno,
                                         line=ln),
                              end='')

    except Exception as err:
        print("grep: {}: {:s}".format(type(err).__name__, err), file=sys.stderr)
        rc = 2 # return code 2 is signaling an error
    
    return rc


if __name__ == "__main__":
    main(sys.argv[1:])
