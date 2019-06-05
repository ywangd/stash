#! python2
# StaSh utility - Dutcho, 16-17 Apr 2017

'''Display output one screen page at a time (optionally with numbered lines)'''

from __future__ import print_function

import argparse
import console
import fileinput
import sys


def msi(chars):
    '''Set terminal screen by ANSI code "MSI", and ignore for non-terminal output'''

    if sys.stdout.isatty():
        msi = u'\u009b'
        sys.stdout.write(msi + chars)


def clear_screen():
    '''Clear terminal screen by ANSI code "MSI c"'''

    msi('c')


def more(filenames, pagesize=10, clear=False, fmt='{line}'):
    '''Display content of filenames pagesize lines at a time (cleared if specified) with format fmt for each output line'''

    fileinput.close()  # in case still open
    try:
        pageno = 1
        if clear:
            clear_screen()
        for line in fileinput.input(
                filenames, openhook=fileinput.hook_encoded("utf-8")):
            lineno, filename, filelineno = fileinput.lineno(
            ), fileinput.filename(), fileinput.filelineno()
            print(fmt.format(**locals()), end='')
            if pagesize and lineno % pagesize == 0:
                # TODO: use less intrusive mechanism than alert
                console.alert('Abort or continue', filename, 'Next page')
                pageno += 1
                if clear:
                    clear_screen()
    finally:
        fileinput.close()

# --- main


def main(args):
    parser = argparse.ArgumentParser(description=__doc__,
                                     epilog='This is inefficient for long input, as StaSh pipes do not multitask')
    parser.add_argument(
        'file',
        help='files to display ("-" is stdin is default)',
        action='store',
        nargs='*')
    parser.add_argument(
        '-p',
        '--pageno',
        help='number screen pages cumulatively',
        action='store_true')
    parser.add_argument(
        '-l',
        '--lineno',
        help='number lines cumulatively',
        action='store_true')
    parser.add_argument(
        '-f',
        '--filename',
        help='label lines by filename',
        action='store_true')
    parser.add_argument(
        '-n',
        '--filelineno',
        '-#',
        help='number lines per file',
        action='store_true')
    parser.add_argument('-s', '--pagesize', help='number of lines per screen page (0 for no pagination)', action='store',
                        type=int, default=40)  # TODO: use actual number of lines on screen for dynamic screen page size
    parser.add_argument(
        '-c',
        '--clear',
        help='clear terminal screen before each screen page',
        action='store_true')
    ns = parser.parse_args(args)
    ns.line = True
    fmt = ' '.join(
        '{' +
        var +
        '}' for var in 'pageno lineno filename filelineno line'.split() if getattr(
            ns,
            var))
    more(ns.file, ns.pagesize, ns.clear, fmt)


if __name__ == "__main__":
    main(sys.argv[1:])
