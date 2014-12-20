'''Display the docstring for a command in /bin, or list all commands if no name is given.
'''

from __future__ import print_function

import argparse
import ast
import os
import sys

def main(args):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cmd", nargs="?", help="the command to get the docstring from")
    ns = ap.parse_args(args)
    
    bin_paths = os.environ["BIN_PATH"].split(os.pathsep)
    
    if not ns.cmd:
        cmds = []
        for path in bin_paths:
            if os.path.exists(path):
                cmds += [
                    fn[:-3] for fn in os.listdir(path)
                    if fn.endswith(".py")
                    and not fn.startswith(".")
                    and os.path.isfile(os.path.join(path, fn))
                ]
        
        if len(cmds) > 100:
            if raw_input("List all {} commands?".format(len(cmds))).strip().lower() not in ("y", "yes"):
                sys.exit(0)
        
        cmds.sort()
        
        print("\n".join(cmds))
    else:
        filename = None
        for path in bin_paths:
            if os.path.exists(path) and ns.cmd + ".py" in os.listdir(path):
                filename = os.path.join(path, ns.cmd + ".py")
                break
        
        if not filename:
            print("man: command '{}' not found".format(ns.cmd))
        
        try:
            with open(filename) as f:
                tree = ast.parse(f.read(), os.path.basename(filename))
        except Exception as err:
            print("man: {}: {!s}".format(type(err).__name__, err), file=sys.stderr)
            sys.exit(1)
        
        docstring = ast.get_docstring(tree)
        if docstring:
            print("Docstring of command '{}':\n{}".format(ns.cmd, docstring))
        else:
            print("man: command '{}' has no docstring".format(ns.cmd))
        
        sys.exit(0)

if __name__ == "__main__":
    main(sys.argv[1:])
