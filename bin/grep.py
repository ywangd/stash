# -*- coding: utf-8 -*-
"""Search a regular expression pattern in one or more files"""

from __future__ import print_function

import os
import io
import re
import sys
import argparse
import fileinput
import fnmatch
from six import PY3

if PY3:
    from pathlib import Path
else:
    from pathlib2 import Path

_stash = globals()['_stash']
abbreviate = _stash.libcore.abbreviate

new_file = True
count = 0        
ns = None
fn = None

def open_hook(filename,mode):
    global fn
    global new_file
    global count
    global ns
    global abbreviate
    
    if fn:
        print_on_count(fn)
    new_file = True
    count = 0
    if filename:
        fn = abbreviate(filename)
        return io.open(filename,mode=mode,encoding='latin1')
    else:
        fn = ns.label
        return None


def print_on_count(filename):
    global count
    global ns
    if (ns.count and (ns.files_without_match or count>0)):
        print(u'{cnt:6} {fn}'
              .format(cnt=count,fn=filename))
    elif ns.files_without_match and count==0:
        print(filename)
            
def main(args):
    global fn
    global new_file
    global count
    global ns
    global _stash
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
    ns = ap.parse_args(args)

    flags = 0
    if ns.ignore_case:
        flags |= re.IGNORECASE

    pattern = re.compile(ns.pattern, flags=flags)

    files = []
    if ns.recursive:
        for f in ns.files:
            if f=="-":
                files.append(f)
            else:
                p = Path(f)
                if p.is_dir():
                    files += [ str(ff.resolve()) for ff in p.rglob('*') if ff.is_file()]
                else:
                    d = p.parent
                    n = p.name
                    files += [ str(ff.resolve()) for ff in d.rglob(n) if ff.is_file()]
    elif len(ns.files)>0:
        # Do not try to grep directories
        for f in ns.files:
            if f=="-":
                files.append(f)
            else:
                p = Path(f)
                if p.is_file():
                    files.append(str(p.resolve()))
                elif not p.exists():
                    _stash.write_message('{} was skipped because it does not exist'.format(f),prefix="grep: ",error=True)
                else:
                    _stash.write_message('{} was skipped because it is not a file'.format(f),prefix="grep: ",error=True)
        if len(files)==0:
            _stash.write_message('No valid files given. Aborting.',prefix="grep: ",error=True)
            return
                

    no_filename = (len(files)<=1)
    if ns.no_filename:
        no_filename = True
    if ns.with_filename:
        no_filename = False
        
    if no_filename:
        if ns.line_number:
            fmt = u'{lineno}: {line}'
        else:
            fmt = u'{line}'
    elif ns.line_number:
        fmt = u'{filename}: {lineno}: {line}'
    else:
        fmt = u'{filename}: {line}'
    
    fileinput.close()  # in case it is not closed
    try:
        count = 0
        lastfile = None
        for line in fileinput.input(files, openhook=open_hook):
            if fileinput.isfirstline() and fileinput.isstdin():
                # simulate open for stdin
                open_hook(None,None)
                
            if bool(pattern.search(line))!=ns.invert:
                count += 1
                if (ns.files_with_matches
                    and not ns.invert):
                    print(fn)
                    fileinput.nextfile()
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
                        print(fmt.format(filename=fn, lineno=fileinput.filelineno(), line=ln),end='')

        print_on_count(fn)

    except Exception as err:
        print("grep: {}: {!s}".format(type(err).__name__, err), file=sys.stderr)
    finally:
        fileinput.close()


if __name__ == "__main__":
    main(sys.argv[1:])
