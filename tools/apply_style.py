"""
Apply the style rules to the source.
"""
import argparse
import os
import sys
import time

from yapf.yapflib.yapf_api import FormatFile

try:
    from .common import get_stash_dir
except (ImportError, ValueError):
    from common import get_stash_dir


def apply_to_file(fp, sp, in_place=False):
    """
    Apply the style to a file.
    :param fp: path to file
    :type fp: str
    :param sp: path to style
    :type sp: str
    :param in_place: format code in-place
    :type in_place: bool
    :return: the reformated code
    :rtype: str or None
    """
    rc, encoidng, changed = FormatFile(fp, style_config=sp, verify=True, in_place=in_place)
    return rc


def apply_to_dir(path, style, recursive=False, in_place=False, verbose=False, pyonly=True):
    """
    Apply the style to all files in a directory.
    :param path: path to directory
    :type path: str
    :param style: path to style file
    :type style: str
    :param recursive: also descend into subdirectories
    :type recursive: bool
    :param in_place: apply the changes directly to the file
    :type in_place: bool
    :param verbose: print additional information
    :type verbose: bool
    :param pyonly: only apply to .py files
    :type pyonly: bool
    """
    if verbose:
        print("Applying style to directory '{}'...".format(path))
    for fn in os.listdir(path):
        fp = os.path.join(path, fn)
        if os.path.isdir(fp) and recursive:
            apply_to_dir(fp, style, recursive=recursive, in_place=in_place, verbose=verbose, pyonly=pyonly)
        elif os.path.isfile(fp):
            if (not fn.endswith(".py")) and pyonly:
                if verbose:
                    print("Skipping '{}' (non-py)...".format(fp))
                continue
            if verbose:
                print("Applying style to file '{}'...".format(fp))
            res = apply_to_file(fp, style, in_place=in_place)
            if not in_place:
                print("# ======= {} =======".format(fp))
                print(res)


def main():
    """the main function"""
    parser = argparse.ArgumentParser(description="Reformat source to follow style rules")
    parser.add_argument("action", help="action to perform", choices=["apply"])
    parser.add_argument("-p", "--path", action="store", help="path to file/directory")
    parser.add_argument("-s", "--style", action="store", help="path to style file")
    parser.add_argument("-r", "--recursive", action="store_true", help="descend into subdirectories")
    parser.add_argument("-v", "--verbose", action="store_true", help="be more verbose")
    parser.add_argument("-i", "--inplace", action="store_true", help="apply the changes to the source")
    parser.add_argument("-a", "--all", action="store_true", help="apply to all files (not just *.py files)")

    ns = parser.parse_args()

    if ns.path is not None:
        path = ns.path
    else:
        path = get_stash_dir()

    if ns.style is not None:
        style = ns.style
    else:
        style = os.path.join(get_stash_dir(), "tools", "yapf.ini")

    if ns.action == "apply":
        start = time.time()
        if not os.path.exists(path):
            print("Error: path '{}' does not exists!".format(path))
            sys.exit(1)
        elif os.path.isdir(path):
            apply_to_dir(path, style, in_place=ns.inplace, recursive=ns.recursive, pyonly=(not ns.all), verbose=ns.verbose)
        else:
            res = apply_to_file(path, style, in_place=ns.inplace)
            if not ns.inplace:
                print(res)
        end = time.time()
        if ns.verbose:
            print("Done. Style applied in {}s".format(end-start))

if __name__ == "__main__":
    main()
