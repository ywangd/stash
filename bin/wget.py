""" Download a file from a url.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from __future__ import unicode_literals

import sys

import requests

import argparse
# from io import open

try:
    import clipboard
    import console
except:
    pass


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

        r = requests.get(url, stream=True)
        file_size = r.headers.get('Content-Length')
        if file_size is not None:
            file_size = int(file_size)

        print("Save as: %s " % output_file, end=' ')
        print("(%s bytes)" % file_size if file_size else "")

        with open(output_file, 'wb') as outs:
            file_size_dl = 0
            block_sz = 8192

            for chunk in r.iter_content(block_sz):
                file_size_dl += len(chunk)
                outs.write(chunk)
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
