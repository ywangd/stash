# -*- coding: utf-8 -*-
# Example of accessing the shell object from script
# This ability completely removes the need of plugins
"""List or define shell aliases."""
from __future__ import print_function

import sys
import argparse

def main(args):
    ap = argparse.ArgumentParser()
    ap.add_argument('expr', nargs='?', help='name=value')
    
    ns = ap.parse_args(args)
    
    app = globals()['_stash']
    """:type : StaSh"""

    _, current_state = app.runtime.get_current_worker_and_state()

    if ns.expr is None:
        for k, v in current_state.aliases.items():
            print('{}={}'.format(k, v[0]))
    
    else:
        if "=" in ns.expr:
            name, value = ns.expr.split("=", 1)
            if name == "" or value == "":
                raise ValueError("alias: invalid name=value expression")

            tokens, parsed = app.runtime.parser.parse(value)
            # Ensure the actual form of an alias is fully expanded
            tokens, _ = app.runtime.expander.alias_subs(tokens, parsed, exclude=name)
            value_expanded = ' '.join(t.tok for t in tokens)
            current_state.aliases[name] = (value, value_expanded)
            sys.exit(0)
        else:
            try:
                print('{}={}'.format(ns.expr, current_state.aliases[ns.expr]))
            except KeyError as err:
                raise KeyError('alias: {} not found'.format(err.message))

if __name__ == "__main__":
    main(sys.argv[1:])
