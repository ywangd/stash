import os
import sys
import re
import fileinput
import argparse

ap = argparse.ArgumentParser()
ap.add_argument('pattern', nargs=1, help='the pattern to search')
ap.add_argument('files', nargs='*', help='files to be searched')
ap.add_argument('-i', '--ignore-case', action='store_true', default=False,
                help='ignore case while searching')
ap.add_argument('-v', '--invert', action='store_true', default=False,
                help='invert the search result')
args = ap.parse_args()

flags = 0
if args.ignore_case:
    flags |= re.IGNORECASE

pattern = re.compile(args.pattern[0], flags=flags)

if args.invert:
    def fn_predicate(test):
        return not test
else:
    def fn_predicate(test):
        return test

# Do not try to grep directories
files = [f for f in args.files if not os.path.isdir(f)]

try:
    fileinput.close()  # in case it is not closed
    for line in fileinput.input(files):
        if fileinput.isstdin():
            fmt = '{lineno}: {line}'
        else:
            fmt = '{filename}: {lineno}: {line}'
        if fn_predicate(pattern.search(line)):
            print fmt.format(filename=fileinput.filename(),
                             lineno=fileinput.filelineno(),
                             line=line.rstrip())

finally:
    fileinput.close()