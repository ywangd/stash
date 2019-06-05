# -*- coding: utf-8 -*-
"""Display help for a command in $STASH_ROOT/bin/ or a topic, or list all commands if no name is given.
"""

from __future__ import print_function

import argparse
import ast
import os
import sys

from stash.system.shcommon import _STASH_EXTENSION_BIN_PATH, _STASH_EXTENSION_MAN_PATH

try:
    raw_input
except NameError:
    # py3
    raw_input = input

_stash = globals()["_stash"]

TYPE_CMD = "command"
TYPE_PAGE = "page"
TYPE_NOTFOUND = "not found"
TYPE_LISTTOPICS = "list topics"

MAIN_BINPATH = os.path.join(os.environ["STASH_ROOT"], "bin")
MAIN_PAGEPATH = os.path.join(os.environ["STASH_ROOT"], "man")

BINPATHS = [MAIN_BINPATH, _STASH_EXTENSION_BIN_PATH]
PAGEPATHS = [MAIN_PAGEPATH, _STASH_EXTENSION_MAN_PATH]

for p in BINPATHS + PAGEPATHS:
    if not os.path.exists(p):
        os.mkdir(p)


def all_commands():
    all_cmds = []
    for bp in BINPATHS:
        cmds = [
            fn[:-3] for fn in os.listdir(bp)
            if fn.endswith(".py")
            and not fn.startswith(".")
            and os.path.isfile(os.path.join(bp, fn))
        ]
        all_cmds += cmds
    all_cmds.sort()
    return all_cmds


def get_type(search):
    """returns (type, path) for a given topic/command."""
    if search == "topics":
        return (TYPE_LISTTOPICS, None)
    cmdpath = find_command(search)
    if cmdpath is not None:
        return (TYPE_CMD, cmdpath)
    if "(" in search and ")" in search:
        try:
            pn = int(search[search.index("(") + 1:search.index(")")])
        except BaseException:
            print(_stash.text_color("Invalid Pagenumber", "red"))
            sys.exit(1)
        search = search[:search.index("(")]
    else:
        pn = 1
    if "." in search:
        # FIXME: fix '.' in search shoild search only matching extensions
        # Example: 'man test.md' searches for 'test.md' instead of 'test'
        print(
            _stash.text_color(
                "Searching for pages with '.' in the name is bugged and has been disabled.",
                "red")
        )
        sys.exit(1)
        to_search = search
        found = []
        for pp in PAGEPATHS:
            found += os.listdir(pp)
    else:
        to_search = search
        found = []
        for p in PAGEPATHS:
            found += [(fn[:fn.index(".")] if "." in fn else fn)
                      for fn in os.listdir(p)]
    if to_search in found:
        ppc = []
        for pp in PAGEPATHS:
            ppc += [(fn, pp) for fn in os.listdir(pp)]
        ffns = [
            (fn,
             pp) if fn.startswith(
                to_search +
                ".") else None for fn,
            pp in ppc]
        ffn = list(filter(None, ffns))
        if len(ffn) == 0:
            # isdir
            pname = "page_" + str(pn)
            for pp in PAGEPATHS:
                dirpath = os.path.join(pp, to_search)
                if not os.path.exists(dirpath):
                    continue
                for fn in os.listdir(dirpath):
                    if fn.startswith(pname):
                        fp = os.path.join(dirpath, fn)
                        if not os.path.exists(fp):
                            print(
                                _stash.text_color("Page not found!", "red")
                            )
                        return (TYPE_PAGE, fp)
            return (TYPE_NOTFOUND, None)
        path = os.path.join(ffn[0][1], ffn[0][0])
        return (TYPE_PAGE, path)
    else:
        return (TYPE_NOTFOUND, None)


def find_command(cmd):
    for bp in BINPATHS:
        if os.path.exists(bp) and cmd + ".py" in os.listdir(bp):
            return os.path.join(bp, cmd + ".py")
    return None


def get_docstring(filename):
    try:
        with open(filename) as f:
            tree = ast.parse(f.read(), os.path.basename(filename))
        return ast.get_docstring(tree)
    except BaseException:
        return "UNKNOWN"


def get_summary(filename):
    docstring = get_docstring(filename)
    return docstring.splitlines()[0] if docstring else ''


def show_page(path):
    """shows the page at path."""
    if not os.path.exists(path):
        print(
            _stash.text_color("Error: cannot find page!", "red"),
        )
        sys.exit(1)
    with open(path, "r") as fin:
        content = fin.read()
    if len(content.replace("\n", "")) == 0:
        print(
            _stash.text_color("Error: help empty!", "red")
        )
        sys.exit(1)
    if path.endswith(".txt"):
        show_text(content)
    elif path.endswith(".url"):
        if content.startswith("stash://"):
            # local file
            path = os.path.join(
                os.getenv("STASH_ROOT"), content.replace("stash://", "")
            )
            show_page(path.replace("\n", ""))
            return
        print("Opening webviewer...")
        _stash("webviewer -n '{u}'".format(u=content.replace("\n", "")))
    elif path.endswith(".html"):
        print("Opening quicklook...")
        _stash("quicklook {p}".format(p=path))
    else:
        show_text(content)


def show_text(text):
    print(_stash.text_color("=" * 20, "yellow"))
    lines = text.split("\n")
    while True:
        if len(lines) < 100:
            print("\n".join(lines))
            return
        else:
            print("\n".join(lines[:100]))
            lines = lines[100:]
            prompt = _stash.text_color("(Press Return to continue)", "yellow")
            raw_input(prompt)
    print("\n")


def show_topics():
    """prints all available miscellaneous help topics."""
    print(_stash.text_color("Miscellaneous Topics:", "yellow"))
    for pp in PAGEPATHS:
        if not os.path.isdir(pp):
            continue
        content = os.listdir(pp)
        for pn in content:
            if "." in pn:
                name = pn[:pn.index(".")]
            else:
                name = pn
            print(name)


def main(args):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "topic",
        nargs="?",
        help="the command/topic to get help for")
    ns = ap.parse_args(args)

    if not ns.topic:
        cmds = all_commands()
        if len(cmds) > 100:
            if raw_input("List all {} commands?".format(len(cmds))
                         ).strip().lower() not in ("y", "yes"):
                sys.exit(0)
        for cmd in cmds:
            print(
                _stash.text_bold('{:>11}: '.format(cmd)) +
                get_summary(find_command(cmd))
            )
        print("Type 'man topics' to see miscellaneous help topics")
        sys.exit(0)
    else:
        ft, path = get_type(ns.topic)
        if ft == TYPE_NOTFOUND:
            print(
                _stash.text_color(
                    "man: no help for '{}'".format(
                        ns.topic), "red")
            )
            sys.exit(1)
        if ft == TYPE_LISTTOPICS:
            show_topics()
            sys.exit(0)
        elif ft == TYPE_CMD:
            try:
                docstring = get_docstring(path)
            except Exception as err:
                print(
                    _stash.text_color(
                        "man: {}: {!s}".format(
                            type(err).__name__, err), "red"),
                    file=sys.stderr
                )
                sys.exit(1)

            if docstring:
                print(
                    "Docstring of command '{}':\n{}".format(
                        ns.topic, docstring))
            else:
                print(
                    _stash.text_color(
                        "man: command '{}' has no docstring".format(ns.topic),
                        "red")
                )
            sys.exit(0)
        elif ft == TYPE_PAGE:
            show_page(path)
            sys.exit(0)


if __name__ == "__main__":
    main(sys.argv[1:])
