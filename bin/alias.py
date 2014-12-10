# Example of accessing the shell object from script
# This ability completely removes the need of plugins
import sys
import argparse

ap = argparse.ArgumentParser()
ap.add_argument('expr', nargs='?', help='name=value')

args = ap.parse_args()

app = globals()['_stash']
rt = app.runtime
 
if args.expr is None:
    for k, v in rt.aliases.items():
        print '%s=%s' % (k, v)

else:
    for i, c in enumerate(args.expr):
        if c == '=':
            name, value = args.expr[0:i], args.expr[i+1:]
            if name == '' or value == '':
                raise Exception('alias: invalid name=value expression')
            else:
                rt.aliases[name] = value
            sys.exit(0)
    else:
        if args.expr in rt.aliases.keys():
            print '%s=%s' % (args.expr, rt.aliases[args.expr])
        else:
            raise Exception('alias: %s not found' % args.expr)
