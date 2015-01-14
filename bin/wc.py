""" Print newline, word, and byte counts for each FILE, and a total line if
more than one FILE is specified.
"""
import os
import sys
import argparse

_stash = globals()['_stash']

def main(args):
    ap = argparse.ArgumentParser()

    ap.add_argument('-l', '--lines',
                    action='store_true',
                    default=False,
                    help='print the newline counts')
    ap.add_argument('files', nargs='*', help='files to count')
    ns = ap.parse_args(args)

    if ns.lines:
        def _print_res(res):
            print '%6d %s' % (res[0], res[-1])
    else:
        def _print_res(res):
            print '%6d %8d %8d %s' % res

    results = []
    nl_count = 0
    wd_count = 0
    bt_count = 0
    filename_old = None
    for infields in _stash.libcore.input_stream(ns.files):
        if filename_old is None:
            filename_old = infields[1]

        if infields[0] is None:
            _, filename, e = infields
            print '%s: %s' % (filename, repr(e))
            filename_old = None
        else:
            line, filename, lineno = infields
            if filename != filename_old:
                results.append((nl_count, wd_count, bt_count, filename_old))
                nl_count = 0
                wd_count = 0
                bt_count = 0
                filename_old = filename

            nl_count += 1
            # TODO: This is not a very accurate for words
            wd_count += len(line.split())
            bt_count += len(line)

    # last file
    results.append((nl_count, wd_count, bt_count, filename_old))

    tot_nl_count = 0
    tot_wd_count = 0
    tot_bt_count = 0
    for res in results:
        _print_res(res)
        tot_nl_count += res[0]
        tot_wd_count += res[1]
        tot_bt_count += res[2]

    if len(results) > 1:
        _print_res((tot_nl_count, tot_wd_count, tot_bt_count, 'total'))


if __name__ == '__main__':
    main(sys.argv[1:])