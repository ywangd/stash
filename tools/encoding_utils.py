#!python2
# -*- coding: utf-8 -*-
"""add encoding lines at the start of the files"""

import os
import argparse
import re
import sys

try:
    from .common import get_stash_dir
except (ImportError, ValueError):
    from common import get_stash_dir

DEFAULT_ENCODING = "utf-8"  # encoding to use to set encoding


def is_encoding_line(s):
    """
    Check if the given line specifies an encoding.
    :param s: line to check
    :type s: str
    :return: whether the given line specifies an encoding or not
    :rtype:  bool
    """
    return get_encoding_from_line(s) is not None


def get_encoding_from_line(s):
    """
    Return the encoding specified in the given line or None if none was specified.
    :param s: line to check
    :type s: str
    :return: the encoding
    :rtype: bool or None
    """
    exp = "^[ \t\f]*#.*?coding[:=][ \t]*([-_.a-zA-Z0-9]+)"
    m = re.match(exp, s)
    if m is None:
        return None
    else:
        return m.groups()[0]


def get_encoding_of_file(p):
    """
    Return the encoding of a file.
    :param p: path to file
    :type p: str
    :return: the encoding of the file or None
    :rtype: str or None
    """
    with open(p, "r") as fin:
        lines = fin.readlines()
        i = 0
        for line in lines:
            i += 1
            if i > 2:
                # encoding must be specified in the first two lines
                return None
            if is_encoding_line(line):
                return get_encoding_from_line(line)


def list_all_encodings(p, recursive=False, ignore_nonpy=False):
    """
    List all files in a directory and their encoding.
    :param p: path to directory
    :type p: str
    :param recursive: whether to descend into subdirectories or not
    :type recursive: bool
    :param ignore_nonpy: skip files not ending with .py
    :type ignore_nonpy: bool
    """
    for fn in os.listdir(p):
        fp = os.path.join(p, fn)
        if os.path.isdir(fp):
            if recursive:
                list_all_encodings(fp, recursive=recursive, ignore_nonpy=ignore_nonpy)
        else:
            if not fn.endswith(".py") and ignore_nonpy:
                # skip
                continue
            show_file_encoding(fp)


def show_file_encoding(p):
    """
    Show the encoding of the file.
    :param p: path to the file
    :type p: str
    """
    enc = get_encoding_of_file(p)
    if enc is None:
        encs = "---"
    else:
        encs = enc
    print("{fn:20} {enc}".format(fn=os.path.relpath(p), enc=encs))


def set_all_encodings(p, encoding, recursive=False, ignore_nonpy=False, force=False):
    """
    Set the encoding for all files in a directory.
    :param p: path to directory
    :type p: str
    :param encoding: encoding to set
    :type encoding: str
    :param recursive: whether to descend into subdirectories or not
    :type recursive: bool
    :param ignore_nonpy: skip files not ending with .py
    :type ignore_nonpy: bool
    :param force: even set the encoding of a file if it already has an encoding
    :type force: bool
    """
    for fn in os.listdir(p):
        fp = os.path.join(p, fn)
        if os.path.isdir(fp):
            if recursive:
                set_all_encodings(
                    fp,
                    encoding,
                    recursive=recursive,
                    ignore_nonpy=ignore_nonpy,
                    force=force,
                )
        else:
            if not fn.endswith(".py") and ignore_nonpy:
                # skip
                continue
            if (get_encoding_of_file(fp) is not None) and not force:
                # skip
                print("Skipping '{}', it already has an encoding.".format(fp))
                continue
            set_file_encoding(fp, encoding)


def set_file_encoding(p, encoding):
    """
    Set the encoding of the file.
    :param p: path to the file
    :type p: str
    :param encoding: encoding to set
    :type encoding: str
    """
    fe = get_encoding_of_file(p)
    if fe is None:
        # we can add the encoding
        to_add = "# -*- coding: {} -*-\n".format(encoding)
        with open(p, "r") as fin:
            lines = fin.readlines()
        if len(lines) == 0:
            # file empty, but we should still add
            lines = [to_add]
        elif lines[0].startswith("#!"):
            # add after shebang
            lines.insert(1, to_add)
        else:
            # add at start
            lines.insert(0, to_add)
        with open(p, "w") as fout:
            fout.write("".join(lines))
    else:
        # we need to overwrite the encoding
        to_add = "# -*- coding: {} -*-\n".format(encoding)
        with open(p, "r") as fin:
            lines = fin.readlines()
        was_set = False
        for i in range(len(lines)):
            line = lines[i]
            if is_encoding_line(line):
                # replace line
                lines[i] = line
                was_set = True
                break
        if not was_set:
            # we should still set the encoding
            if lines[0].startswith("#!"):
                # add after shebang
                lines.insert(1, to_add)
            else:
                # add at start
                lines.insert(0, to_add)


def remove_all_encodings(p, recursive=False, ignore_nonpy=True):
    """
    Set the encoding for all files in a directory.
    :param p: path to directory
    :type p: str
    :param recursive: whether to descend into subdirectories or not
    :type recursive: bool
    :param ignore_nonpy: skip files not ending with .py
    :type ignore_nonpy: bool
    """
    for fn in os.listdir(p):
        fp = os.path.join(p, fn)
        if os.path.isdir(fp):
            if recursive:
                remove_all_encodings(fp, recursive=recursive, ignore_nonpy=ignore_nonpy)
        else:
            if not fn.endswith(".py") and ignore_nonpy:
                # skip
                continue
            if get_encoding_of_file(fp) is None:
                # skip
                print("Skipping '{}', it has no encoding.".format(fp))
                continue
            remove_file_encoding(fp)


def remove_file_encoding(path):
    """
    Remove the encoding line from the given file.
    :param path: path to remove from
    :type path: str
    """
    with open(path, "r") as fin:
        lines = fin.readlines()
        if len(lines) >= 1 and is_encoding_line(lines[0]):
            lines.pop(0)
        elif len(lines) >= 2 and is_encoding_line(lines[1]):
            lines.pop(1)
        else:
            print("No encoding line found in '{}'!".format(path))
            return
    with open(path, "w") as fout:
        fout.write("".join(lines))


def main():
    """the main function"""
    parser = argparse.ArgumentParser(description="encoding tool")
    parser.add_argument(
        "action", action="store", help="what to do", choices=["show", "set", "remove"]
    )
    parser.add_argument(
        "-p", "--path", action="store", help="path to file(s), defaults to StaSh root"
    )
    parser.add_argument(
        "-r", "--recursive", action="store_true", help="descend into subdirectories"
    )
    parser.add_argument(
        "--py-only", dest="pyonly", action="store_true", help="ignore non .py files"
    )
    parser.add_argument("-f", "--force", action="store_true", help="force the action")
    parser.add_argument(
        "-e",
        "--encoding",
        action="store",
        help="encoding to use (required by some actions",
    )

    ns = parser.parse_args()

    if ns.path is not None:
        path = ns.path
    else:
        path = get_stash_dir()
    if ns.encoding is not None:
        encoding = ns.encoding
    else:
        encoding = DEFAULT_ENCODING

    if ns.action == "show":
        if not os.path.exists(path):
            print("Path '{p}' does not exists!".format(p=path))
            sys.exit(1)
        elif os.path.isdir(path):
            list_all_encodings(path, recursive=ns.recursive, ignore_nonpy=ns.pyonly)
        else:
            show_file_encoding(path)
    elif ns.action == "set":
        if not os.path.exists(path):
            print("Path '{p}' does not exists!".format(p=path))
            sys.exit(1)
        elif os.path.isdir(path):
            set_all_encodings(
                path,
                encoding,
                recursive=ns.recursive,
                ignore_nonpy=ns.pyonly,
                force=ns.force,
            )
        else:
            set_file_encoding(path, encoding)
    elif ns.action == "remove":
        if not os.path.exists(path):
            print("Path '{p}' does not exists!".format(p=path))
            sys.exit(1)
        elif os.path.isdir(path):
            remove_all_encodings(path, recursive=ns.recursive, ignore_nonpy=ns.pyonly)
        else:
            remove_file_encoding(path)
    else:
        print("Unknown action: '{}'!".format(ns.action))
        sys.exit(2)


if __name__ == "__main__":
    main()
