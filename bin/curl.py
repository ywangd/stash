#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Transfer a URL using Python's standard library."""

import argparse
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Sequence
from urllib.parse import urlparse

try:
    import clipboard  # type: ignore[import-not-found]
except ImportError:
    clipboard = None


def main(args: Sequence[str]) -> None:
    """Main function to parse arguments and perform the request."""
    clip_url = clipboard.get() if (clipboard and hasattr(clipboard, "get")) else None
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "url",
        default=clip_url,
        nargs="?",
        help="the url to read (default to clipboard)")
    ap.add_argument(
        "-o", "--output-file", type=Path, help="write output to file instead of stdout"
    )
    ap.add_argument(
        "-O",
        "--remote-name",
        action="store_true",
        help="write output to a local file named like the remote file we get",
    )
    ap.add_argument(
        "-L",
        "--location",
        action="store_true",
        help="follow redirects to other web pages (if the URL has a 3XX response code)",
    )
    ap.add_argument(
        "-X",
        "--request-method",
        default="GET",
        choices=["GET", "POST", "HEAD"],
        help="specify request method to use (default to GET)",
    )
    ap.add_argument("-H", "--header", help="Custom header to pass to server (H)")
    ap.add_argument("-d", "--data", help="HTTP POST data (H)")

    ns = ap.parse_args(args)
    url = ns.url

    if not url:
        print("Please provide a URL or have one in the clipboard.", file=sys.stderr)
        sys.exit(1)

    headers = {}
    if ns.header:
        for h in ns.header.split(";"):
            try:
                name, value = h.split(":", 1)
                headers[name.strip()] = value.strip()
            except ValueError:
                print(f"Invalid header format: {h}", file=sys.stderr)
                sys.exit(1)

    data = ns.data.encode("utf-8") if ns.data else None

    # Create a Request object
    req = urllib.request.Request(url, data=data, method=ns.request_method, headers=headers)

    # Handle redirects
    if not ns.location:
        # Create a custom opener that doesn't follow redirects
        # This is the equivalent of allow_redirects=False in requests
        class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
            def http_error_301(self, req, fp, code, msg, headers):
                return fp

            http_error_302 = http_error_303 = http_error_307 = http_error_301

        opener = urllib.request.build_opener(NoRedirectHandler)
    else:
        # By default, urllib.request.urlopen follows redirects
        opener = urllib.request.build_opener()

    try:
        with opener.open(req) as response:
            # Determine output file path
            if ns.output_file:
                output_path = ns.output_file
            elif ns.remote_name:
                url_path = urlparse(url).path
                filename = Path(url_path).name
                output_path = Path(filename)
            else:
                output_path = None

            if output_path:
                # Write to a file
                with open(output_path, "wb") as outs:
                    outs.write(response.read())
            else:
                # Print to stdout
                print(response.read().decode("utf-8"))

    except urllib.error.URLError as e:
        print(f"Error: {e.reason}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nOperation interrupted by user.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
