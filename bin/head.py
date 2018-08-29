"""Print the first 10 lines of the given files.
"""

from __future__ import print_function

import argparse
import string
import sys
import fileinput

def filter_non_printable(s):
    return ''.join([c if c.isalnum() or c.isspace() or c in string.punctuation else ' ' for c in s])

def head(f, nlines):
    if nlines >= 0:
        for i, line in enumerate(f):
            if i >= nlines:
                break
            print(line, end='')
    else:
        buf = []
        print(1)
        line = f.readline()
        print(2)
        while line:
            buf.append(line)
            if len(buf) > -nlines:
                del buf[0]
            line = f.readline()

        for line in buf:
            print(line, end='')

def main(args):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("-n", "--lines",default=10, type=int,
                   help="""print the first K lines instead of 10;
                   if negative, print the last -K lines""")
    p.add_argument("-q", "--quiet", "--silent", action='store_true',
                   help="never print headers for each file")
    p.add_argument("-v", "--verbose", action='store_true',
                   help="always print headers for each file")
    p.add_argument("files", action="store", nargs="*",
                   help="files to print")
    ns = p.parse_args(args)

    status = 0

    header_fmt = '==> {} <==\n'

    if len(ns.files) == 0:
        ns.files = ['-']

    try:
        for fname in ns.files:
            if ns.verbose or (len(ns.files) > 1 and not ns.quiet):
                if fname == '-':
                    print(header_fmt.format('standard input'), end='')
                else:
                    print(header_fmt.format(fname), end='')

            fileinput.close()
            inp = fileinput.input(fname, openhook=fileinput.hook_encoded("utf-8"))
            if ns.lines >= 0:
                buf = []
                for i, line in enumerate(inp):
                    if i >= ns.lines:
                        break
                    buf.append(line)
                for line in buf:
                    print(line, end='')
            else:
                buf = []
                for line in fileinput.input(inp, openhook=fileinput.hook_encoded("utf-8")):
                    buf.append(line)
                    if len(buf) > -ns.lines:
                        del buf[0]
                for line in buf:
                    print(line, end='')

    except Exception as e:
        print('head :%s' % str(e))
        status = 1
    finally:
        fileinput.close()

    sys.exit(status)

if __name__ == "__main__":
    main(sys.argv[1:])
