# coding=utf-8
""" Transfer a URL
"""
from __future__ import print_function
import sys
import argparse
import requests

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

try:
    import clipboard
except ImportError:
    pass


def main(args):
    ap = argparse.ArgumentParser()
    ap.add_argument('url', nargs='?', help='the url to read (default to clipboard')
    ap.add_argument('-o', '--output-file', help='write output to file instead of stdout')
    ap.add_argument(
        '-O',
        '--remote-name',
        action='store_true',
        help='write output to a local file named like the remote file we get'
    )
    ap.add_argument(
        '-X',
        '--request-method',
        default='GET',
        choices=['GET',
                 'POST',
                 'HEAD'],
        help='specify request method to use (default to GET)'
    )
    ap.add_argument('-H', '--header', help='Custom header to pass to server (H)')
    ap.add_argument('-d', '--data', help='HTTP POST data (H)')

    ns = ap.parse_args(args)
    url = ns.url or clipboard.get()

    headers = {}
    if ns.header:
        for h in ns.header.split(';'):
            name, value = h.split(':')
            headers[name.strip()] = value.strip()

    if ns.request_method == 'GET':
        r = requests.get(url, headers=headers)
    elif ns.request_method == 'POST':
        r = requests.post(url, data=ns.data, headers=headers)
    elif ns.request_method == 'HEAD':
        r = requests.head(url, headers=headers)
    else:
        print('unknown request method: {}'.format(ns.request_method))
        return

    if ns.output_file:
        with open(ns.output_file, 'w') as outs:
            outs.write(r.text)
    elif ns.remote_name:
        # get basename of url
        url_path = urlparse(url).path
        filename = url_path.split('/')[-1]
        with open(filename, 'w') as outs:
            outs.write(r.text)
    else:
        print(r.text)


if __name__ == '__main__':
    main(sys.argv[1:])
