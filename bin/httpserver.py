#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Simple HTTP Server With Upload (https://gist.github.com/UniIsland/3346170)

This module builds on BaseHTTPServer by implementing the standard GET
and HEAD requests in a fairly straightforward manner.
"""

import html
import mimetypes
import os
import posixpath
import re
import shutil

from io import BytesIO
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import quote, unquote

__version__ = "0.1"
__all__ = ["SimpleHTTPRequestHandler"]
__author__ = "bones7456"
__home_page__ = "http://li2z.cn/"


class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    """Simple HTTP request handler with GET/HEAD/POST commands.

    This serves files from the current directory and any of its
    subdirectories. The MIME type for files is determined by
    calling the .guess_type() method. It can also receive files uploaded
    by clients.

    The GET/HEAD/POST requests are identical except that the HEAD
    request omits the actual contents of the file.
    """

    server_version = "SimpleHTTPWithUpload/" + __version__

    def do_GET(self):
        """Serve a GET request."""
        f = self.send_head()
        if f:
            self.copy_file(f, self.wfile)
            f.close()

    def do_HEAD(self):
        """Serve a HEAD request."""
        f = self.send_head()
        if f:
            f.close()

    def do_POST(self):
        """Serve a POST request."""
        r, info = self.deal_post_data()
        print(r, info, "by: ", self.client_address)

        f = BytesIO()

        f.write(b'<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">')
        f.write(b"<html>\n<title>Upload Result Page</title>\n")
        f.write(b"<body>\n<h2>Upload Result Page</h2>\n")
        f.write(b"<hr>\n")
        if r:
            f.write(b"<strong>Success:</strong>")
        else:
            f.write(b"<strong>Failed:</strong>")
        f.write(info.encode("utf-8"))
        f.write(b'<br><a href="%s">back</a>' % self.headers["referer"].encode("utf-8"))
        f.write(b"<hr><small>Powered By: bones7456, check new version at ")
        f.write(b'<a href="http://li2z.cn/?s=SimpleHTTPServerWithUpload">')
        f.write(b"here</a>.</small></body>\n</html>\n")

        length = f.tell()
        f.seek(0)
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(length))
        self.end_headers()

        if f:
            self.copy_file(f, self.wfile)
            f.close()

    def deal_post_data(self):
        """
        Handles POST requests for file uploads without using the cgi module.

        Parses the 'Content-Type' header string to manually find the boundary for the
        multipart form data. Reads the request body line by line from
        the rfile stream, locates the file data, and saves it to a file
        in the current directory.

        Returns:
            A tuple (bool, str) indicating success/failure and a message.
        """
        # 1. Manually parse the Content-Type header to find the boundary.
        content_type = self.headers.get("Content-Type")
        if not content_type:
            return False, "Content-Type header is missing."

        # Find the boundary string in the header.
        boundary_match = re.search(r"boundary=(.*)", content_type)
        if not boundary_match:
            return False, "Boundary parameter is missing from Content-Type header."

        # Extract the boundary, removing quotes if they exist.
        boundary_str = boundary_match.group(1).strip()
        if boundary_str.startswith('"') and boundary_str.endswith('"'):
            boundary_str = boundary_str[1:-1]

        # The boundary must be a byte string for comparison with the request body.
        boundary_marker = f"--{boundary_str}".encode("utf-8")

        # 2. Read the request body as a binary stream.
        remainbytes = int(self.headers.get("content-length"))
        line = self.rfile.readline()
        remainbytes -= len(line)

        # Check if the content starts with the boundary marker.
        if boundary_marker not in line:
            return False, "Content does not begin with boundary."

        # 3. Read the header lines for the file part.
        line = self.rfile.readline()
        remainbytes -= len(line)

        # Use a regex pattern for bytes to find the filename.
        fn = re.findall(b'Content-Disposition.*name="file"; filename="(.*)"', line)
        if not fn:
            return False, "Can't find out file name..."

        # Decode the filename from bytes to a string.
        filename = fn[0].decode("utf-8")
        path = self.translate_path(self.path)
        filepath = os.path.join(path, filename)

        line = self.rfile.readline()
        remainbytes -= len(line)
        line = self.rfile.readline()
        remainbytes -= len(line)

        # 4. Open the file to write the content.
        try:
            out = open(filepath, "wb")
        except IOError:
            return (
                False,
                "Can't create file to write, do you have permission to write?",
            )

        # 5. Read the file content and write it to disk.
        pre_line = self.rfile.readline()
        remainbytes -= len(pre_line)
        while remainbytes > 0:
            line = self.rfile.readline()
            remainbytes -= len(line)
            if boundary_marker in line:
                pre_line = pre_line[0:-1]
                if pre_line.endswith(b"\r"):
                    pre_line = pre_line[0:-1]
                out.write(pre_line)
                out.close()
                return True, "File '%s' upload success!" % filename
            else:
                out.write(pre_line)
                pre_line = line

        return False, "Unexpected end of data."

    def send_head(self):
        """Common code for GET and HEAD commands.

        This sends the response code and MIME headers.

        Return value is either a file object (which has to be copied
        to the outputfile by the caller unless the command was HEAD,
        and must be closed by the caller under all circumstances), or
        None, in which case the caller has nothing further to do.
        """
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            if not self.path.endswith("/"):
                # redirect browser - doing basically what apache does
                self.send_response(301)
                self.send_header("Location", self.path + "/")
                self.end_headers()
                return None
            for index in "index.html", "index.htm":
                index = os.path.join(path, index)
                if os.path.exists(index):
                    path = index
                    break
            else:
                return self.list_directory(path)

        # Use try/except to handle the future deprecation of mimetypes.guess_type()
        # and the introduction of mimetypes.guess_filetype() in Python 3.13.
        try:
            # Try to use the new, preferred function first
            ctype = mimetypes.guess_file_type(path)[0]
        except AttributeError:
            # Fall back to the older function if the new one is not available
            ctype = mimetypes.guess_type(path)[0]

        # If no MIME type is found, default to 'application/octet-stream'
        ctype = ctype or "application/octet-stream"

        try:
            f = open(path, "rb")
        except IOError:
            self.send_error(404, "File not found")
            return None

        self.send_response(200)
        self.send_header("Content-type", ctype)
        fs = os.fstat(f.fileno())
        self.send_header("Content-Length", str(fs[6]))
        self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
        self.end_headers()
        return f

    def list_directory(self, path):
        """Helper to produce a directory listing (absent index.html).

        Return value is either a file object, or None (indicating an
        error).  In either case, the headers are sent, making the
        interface the same as for send_head().
        """
        try:
            list_ = os.listdir(path)
        except os.error:
            self.send_error(404, "No permission to list directory")
            return None
        list_.sort(key=lambda a: a.lower())

        f = BytesIO()
        display_path = html.escape(unquote(self.path))

        f.write(b'<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">')
        f.write(
            b"<html>\n<title>Directory listing for %s</title>\n"
            % display_path.encode("utf-8")
        )
        f.write(
            b"<body>\n<h2>Directory listing for %s</h2>\n"
            % display_path.encode("utf-8")
        )
        f.write(b"<hr>\n")
        f.write(b'<form ENCTYPE="multipart/form-data" method="post">')
        f.write(b'<input name="file" type="file"/>')
        f.write(b'<input type="submit" value="upload"/></form>\n')
        f.write(b"<hr>\n<ul>\n")

        for name in list_:
            fullname = os.path.join(path, name)
            display_name = link_name = name
            # Append / for directories or @ for symbolic links
            if os.path.isdir(fullname):
                display_name = name + "/"
                link_name = name + "/"
            if os.path.islink(fullname):
                display_name = name + "@"
                # Note: a link to a directory displays with @ and links with /
            f.write(
                b'<li><a href="%s">%s</a>\n'
                % (
                    quote(link_name).encode("utf-8"),
                    html.escape(display_name).encode("utf-8"),
                )
            )
        f.write(b"</ul>\n<hr>\n</body>\n</html>\n")

        length = f.tell()
        f.seek(0)
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(length))
        self.end_headers()

        return f

    @staticmethod
    def translate_path(path):
        """Translate a /-separated PATH to the local filename syntax.

        Components that mean special things to the local file system
        (e.g. drive or directory names) are ignored.
        """
        # abandon query parameters
        path = path.split("?", 1)[0]
        path = path.split("#", 1)[0]
        path = posixpath.normpath(unquote(path))
        words = path.split("/")
        words = filter(None, words)
        path = os.getcwd()
        for word in words:
            drive, word = os.path.splitdrive(word)
            head, word = os.path.split(word)
            if word in (os.curdir, os.pardir):
                continue
            path = os.path.join(path, word)
        return path

    @staticmethod
    def copy_file(source, outputfile):
        """Copy all data between two file objects.

        The SOURCE argument is a file object open for reading
        and the DESTINATION argument is a file object open for writing.
        """
        shutil.copyfileobj(source, outputfile)


def main(port=8000):
    server = HTTPServer(("0.0.0.0", port), SimpleHTTPRequestHandler)

    try:
        print("Serving HTTP on 0.0.0.0 port %d ..." % port)
        # Note: The following line is specific to the "StaSh" environment and may need to be adjusted
        # if you are running this script in a different terminal.
        _stash = globals().get("_stash", None)
        if _stash:
            print("local IP address is %s" % globals()["_stash"].libcore.get_lan_ip())
        server.serve_forever()

    except KeyboardInterrupt:
        print("Server shutting down ...")
        server.server_close()


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument(
        "port", nargs="?", type=int, default=8000, help="port to server HTTP"
    )
    ns = ap.parse_args()
    main(ns.port)
