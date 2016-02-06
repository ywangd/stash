""" Tip of the day
"""
import os
import sys
import json
import random
import argparse


def main(args):
    ap = argparse.ArgumentParser()
    ap.add_argument('-n', '--count', action='store_true',
                    help='show total number of tips')

    ns = ap.parse_args(args)

    filename = os.path.join(os.environ['STASH_ROOT'], '.stash_tips')
    if not os.path.exists(filename):
        return 1

    _stash = globals()['_stash']

    with open(filename) as ins:
        tips = json.load(ins)

        if ns.count:
            print 'Total available tips: %s' % len(tips)
        else:
            idx = random.randint(0, len(tips) - 1)
            print '%s: %s' % (_stash.text_bold('Tip'),
                              _stash.text_italic(tips[idx]))


if __name__ == '__main__':
    main(sys.argv[1:])
