""" Download a file from a url.
"""
from __future__ import print_function

import sys
import urllib2
import argparse

try:
    import clipboard
    import console
except:
    import dummyconsole as console


def main(args):
    ap = argparse.ArgumentParser()
    ap.add_argument('-o', '--output-file', nargs='?', help='save content as file')
    ap.add_argument('url', nargs='?', help='the url to read from (default to clipboard)')

    ns = ap.parse_args(args)
    url = ns.url or clipboard.get()
    output_file = ns.output_file or url.split('/')[-1]

    console.show_activity()
    try:

        print('Opening: %s' % url)
        u = urllib2.urlopen(url)

        meta = u.info()
        try:
            file_size = int(meta.getheaders("Content-Length")[0])
        except IndexError:
            file_size = 0

        print("Save as: %s " % output_file, end=' ')
        print("(%s bytes)" % file_size if file_size else "")

        with open(output_file, 'wb') as f:
            file_size_dl = 0
            block_sz = 8192
            while True:
                buf = u.read(block_sz)
                if not buf:
                    break
                file_size_dl += len(buf)
                f.write(buf)
                if file_size:
                    status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
                else:
                    status = "%10d" % file_size_dl
                print('\r' + status, end=' ')
            print()

    except:
        print('invalid url: %s' % url)
        sys.exit(1)

    finally:
        console.hide_activity()

    sys.exit(0)


if __name__ == '__main__':
    main(sys.argv[1:])
