"""Sort standard input or a file to standard output"""
import os
import sys
import fileinput
import argparse

def main(args):
    ap = argparse.ArgumentParser()
    ap.add_argument('file', nargs='?', help='the file to be sorted')
    ap.add_argument('-r', '--reverse', action='store_true', default=False,
                    help='reverse the result of comparisons')
    ns = ap.parse_args(args)

    thefile = ns.file if ns.file else None

    if thefile is not None and os.path.isdir(thefile):
        print '%s: Is a directory' % thefile

    else:
        try:
            fileinput.close()  # in case it is not closed
            lines = sorted(line for line in fileinput.input(thefile))
            if ns.reverse:
                lines = lines[::-1]

            print ''.join(lines)

        finally:
            fileinput.close()


if __name__ == '__main__':
    main(sys.argv[1:])