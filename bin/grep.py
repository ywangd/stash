"""Search a regular expression pattern in one or more files"""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from __future__ import unicode_literals

import argparse
import fileinput
import os
import re
import sys

def main(args):
    ap = argparse.ArgumentParser()
    ap.add_argument('pattern', help='the pattern to match')
    ap.add_argument('files', nargs='*', help='files to be searched')
    ap.add_argument('-i', '--ignore-case', action='store_true',
                    help='ignore case while searching')
    ap.add_argument('-v', '--invert', action='store_true',
                    help='invert the search result')
    ns = ap.parse_args(args)

    flags = 0
    if ns.ignore_case:
        flags |= re.IGNORECASE
    
    pattern = re.compile(ns.pattern, flags=flags)
    
    if ns.invert:
        def fn_predicate(line, newline):
            return line == newline
    else:
        def fn_predicate(line, newline):
            return line != newline
    
    # Do not try to grep directories
    files = [f for f in ns.files if not os.path.isdir(f)]
    
    fileinput.close()  # in case it is not closed
    try:
        for line in fileinput.input(files):
            newline = re.sub(pattern, lambda m: _stash.text_color(m.group(), 'red'), line)
            if fn_predicate(line, newline):
                if fileinput.isstdin():
                    fmt = u'{lineno}: {line}'
                else:
                    fmt = u'{filename}: {lineno}: {line}'

                print(fmt.format(filename=fileinput.filename(),
                                 lineno=fileinput.filelineno(),
                                 line=newline.rstrip()))
    except Exception as err:
        print("grep: {}: {!s}".format(type(err).__name__, err), file=sys.stderr)
    finally:
        fileinput.close()

if __name__ == "__main__":
    main(sys.argv[1:])
