from __future__ import print_function

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
        def fn_predicate(test):
            return not test
    else:
        def fn_predicate(test):
            return test
    
    # Do not try to grep directories
    files = [f for f in ns.files if not os.path.isdir(f)]
    
    fileinput.close()  # in case it is not closed
    try:
        for line in fileinput.input(files):
            if fn_predicate(pattern.search(line)):
                if fileinput.isstdin():
                    fmt = '{lineno}: {line}'
                else:
                    fmt = '{filename}: {lineno}: {line}'
                
                print(fmt.format(filename=fileinput.filename(),
                                 lineno=fileinput.filelineno(),
                                 line=line.rstrip()))
    except Exception as err:
        print("grep: {}: {!s}".format(type(err).__name__, err), file=sys.stderr)
    finally:
        fileinput.close()

if __name__ == "__main__":
    main(sys.argv[1:])
