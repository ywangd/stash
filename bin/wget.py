# -*- coding: utf-8 -*-
""" Download a file from a url.
"""
from __future__ import print_function

import sys
import argparse
import ssl

from six.moves.urllib.request import urlopen

import certifi

try:
    import console
except ImportError:
    console = None

_stash = globals()["_stash"]


def get_status_string(downloaded, total):
    """Return a string showing the current progress"""
    if _stash is not None and hasattr(_stash, "libcore"):
        hdr = _stash.libcore.sizeof_fmt(downloaded)
    else:
        hdr = "%10d" % downloaded
    if total:
        total = float(total)
        percent = min((downloaded / total) * 100.0, 100.0)
        total_c = 20
        nc = int(total_c * (downloaded / total))
        sh = ">" if downloaded != total else "="
        bar = "[" + "=" * (nc - 1) + sh + " " * (total_c - nc) + "]"
        # status = r"%10d  [%3.2f%%]" % downloaded, percent
        status = r"%s %3.2f%% | %s" % (bar, percent, hdr)
    else:
        status = hdr
    return status


def main(args):
    ap = argparse.ArgumentParser()
    ap.add_argument('-o', '--output-file', nargs='?', help='save content as file')
    ap.add_argument('url', nargs='?', help='the url to read from (default to clipboard)')

    ns = ap.parse_args(args)
    url = ns.url or _stash.libdist.clipboard_get()
    output_file = ns.output_file or url.split('/')[-1]

    if console is not None:
        console.show_activity()

    try:

        print('Opening: %s\n' % url)
        context = ssl.create_default_context(cafile=certifi.where())
        u = urlopen(url, context=context)

        meta = u.info()
        try:
            if _stash.PY3:
                file_size = int(meta["Content-Length"])
            else:
                file_size = int(meta.getheaders("Content-Length")[0])
        except (IndexError, ValueError, TypeError):
            file_size = 0

        print("Save as: {} ".format(output_file), end="")
        print("({} bytes)".format(file_size if file_size else "???"))

        with open(output_file, 'wb') as f:
            file_size_dl = 0.0
            block_sz = 8192
            while True:
                buf = u.read(block_sz)
                if not buf:
                    break
                file_size_dl += len(buf)
                f.write(buf)
                status = get_status_string(file_size_dl, file_size)
                print('\r' + status + " " * 10, end="")
            print("")

    except Exception as e:
        print('Invalid url: %s' % url)
        sys.exit(1)

    finally:
        if console is not None:
            console.hide_activity()

    sys.exit(0)


if __name__ == '__main__':
    main(sys.argv[1:])
