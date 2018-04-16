""" List and set StaSh configuration options """
from __future__ import print_function

import sys
import argparse

_stash = globals()['_stash']

def main(args):
    ap = argparse.ArgumentParser()
    ap.add_argument('name', nargs='?', help='variable name')
    ap.add_argument('value', nargs='?', type=int, help='variable value')
    ap.add_argument('-l', '--list', action='store_true',
                    help='list all config variables and their values')
    ns = ap.parse_args(args)

    config = {
        'py_traceback': _stash.runtime,
        'py_pdb': _stash.runtime,
        'input_encoding_utf8': _stash.runtime,
        'ipython_style_history_search': _stash.runtime,
    }

    if ns.list:
        for name in sorted(config.keys()):
            print('%s=%s' % (name, config[name].__dict__[name]))

    else:
        try:
            if ns.name is not None and ns.value is not None:
                config[ns.name].__dict__[ns.name] = ns.value
            elif ns.name is not None:
                print('%s=%s' % (ns.name, config[ns.name].__dict__[ns.name]))
            else:
                ap.print_help()

        except KeyError:
            print('%s: invalid config option name' % ns.name)
            sys.exit(1)


if __name__ == '__main__':
    main(sys.argv[1:])
