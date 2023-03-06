# coding=utf-8
""" Transfer a URL
"""
from __future__ import print_function
import sys
import argparse
import requests

from six.moves.urllib.parse import urlparse

try:
    import clipboard
except ImportError:
    clipboard = None


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
        '-L',
        '--location',
        action='store_true',
        help='follow redirects to other web pages (if the URL has a 3XX response code)'
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
    ap.add_argument('-H', '--header', help='Custom header to pass to server (H)', action='append')
    ap.add_argument('-d', '--data', help='HTTP POST data (H)')

    ns = ap.parse_args(args)
    url = ns.url or clipboard.get()

    headers = {}
    for header in ns.header:
        for h in header.split(';'):
            name, value = h.split(':')
            headers[name.strip()] = value.strip()

    if ns.request_method == 'GET':
        r = requests.get(
            url,
            headers=headers,
            allow_redirects=ns.location
        )
    elif ns.request_method == 'POST':
        r = requests.post(
            url,
            data=ns.data,
            headers=headers,
            allow_redirects=ns.location
        )
    elif ns.request_method == 'HEAD':
        r = requests.head(
            url,
            headers=headers,
            allow_redirects=ns.location
        )
    else:
        print('unknown request method: {}'.format(ns.request_method))
        return

    if ns.output_file:
        with open(ns.output_file, 'wb') as outs:
            outs.write(r.content)
    elif ns.remote_name:
        # get basename of url
        url_path = urlparse(url).path
        filename = url_path.split('/')[-1]
        with open(filename, 'wb') as outs:
            outs.write(r.content)
    else:
        if ns.request_method == 'HEAD':
            print('Status: {}'.format(r.status_code))
            for k, v in r.headers.items():
                print('{}: {}'.format(k, v))
            print('')
        else:
            print(r.text)


if __name__ == '__main__':
    main(sys.argv[1:])
