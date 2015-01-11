# Example of accessing the shell object from script
# This ability completely removes the need of plugins
"""List or define shell aliases."""
from __future__ import print_function

import sys
import argparse

def main(args):
    ap = argparse.ArgumentParser()
    ap.add_argument('expr', nargs='?', help='name=value')
    
    args = ap.parse_args(args)
    
    app = globals()['_stash']
    rt = app.runtime
     
    if args.expr is None:
        for k, v in rt.aliases.items():
            print('{}={}'.format(k, v[0]))
    
    else:
        if "=" in args.expr:
            name, value = args.expr.split("=", 1)
            if name == "" or value == "":
                raise ValueError("alias: invalid name=value expression")

            tokens, parsed = app.runtime.parser.parse(value)
            # Ensure the actual form of an alias is fully expanded
            tokens, _ = app.runtime.expander.alias_subs(tokens, parsed, exclude=name)
            value_expanded = ' '.join(t.tok for t in tokens)
            rt.aliases[name] = (value, value_expanded)
            sys.exit(0)
        else:
            try:
                print('{}={}'.format(args.expr, rt.aliases[args.expr]))
            except KeyError as err:
                raise KeyError('alias: {} not found'.format(err.message))

if __name__ == "__main__":
    main(sys.argv[1:])
