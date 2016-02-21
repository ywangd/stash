"""Display the docstring for a command in $STASH_ROOT/bin/, or list all commands if no name is given.
"""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from __future__ import unicode_literals

import argparse
import ast
import os
import sys
from six.moves import input


def all_commands():
    path = os.path.join(os.environ['STASH_ROOT'], 'bin')
    cmds = [
        fn[:-3] for fn in os.listdir(path)
        if fn.endswith(".py")
        and not fn.startswith(".")
        and os.path.isfile(os.path.join(path, fn))
    ]
    cmds.sort()
    return cmds

def find_command(cmd):
    path = os.path.join(os.environ['STASH_ROOT'], 'bin')
    if os.path.exists(path) and cmd + ".py" in os.listdir(path):
        return os.path.join(path, cmd + ".py")
    return None

def get_docstring(filename):
    with open(filename) as f:
        tree = ast.parse(f.read(), os.path.basename(filename))
    return ast.get_docstring(tree)

def get_summary(filename):
    docstring = get_docstring(filename)
    return docstring.splitlines()[0] if docstring else ''

def main(args):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cmd", nargs="?", help="the command to get the docstring from")
    ns = ap.parse_args(args)
    
    if not ns.cmd:
        cmds = all_commands()
        if len(cmds) > 100:
            if input("List all {} commands?".format(len(cmds))).strip().lower() not in ("y", "yes"):
                sys.exit(0)
        for cmd in cmds:
            print(_stash.text_bold('{:>10}: '.format(cmd)) + get_summary(find_command(cmd)))
    else:
        filename = find_command(ns.cmd)
        
        if not filename:
            print("man: command '{}' not found".format(ns.cmd))
            sys.exit(1)
            
        try:
            docstring = get_docstring(filename)
        except Exception as err:
            print("man: {}: {!s}".format(type(err).__name__, err), file=sys.stderr)
            sys.exit(1)

        if docstring:
            print("Docstring of command '{}':\n{}".format(ns.cmd, docstring))
        else:
            print("man: command '{}' has no docstring".format(ns.cmd))
        
        sys.exit(0)

if __name__ == "__main__":
    main(sys.argv[1:])
