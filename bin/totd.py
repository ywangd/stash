# -*- coding: utf-8 -*-
"""Tip of the day"""

import argparse
import json
import os
import random
import sys


def main(args):
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "-n", "--count", action="store_true", help="show total number of tips"
    )

    ns = ap.parse_args(args)

    try:
        filename = os.path.join(os.environ["STASH_ROOT"], "data", "stash_tips.json")
        if not os.path.exists(filename):
            return 1

        _stash = globals().get("_stash")
        if _stash is None:
            raise RuntimeError("StaSh runtime not found")

        with open(filename) as ins:
            tips = json.load(ins)

            if ns.count:
                print("Total available tips: %s" % len(tips))
            else:
                idx = random.randint(0, len(tips) - 1)
                print("%s: %s" % (_stash.text_bold("Tip"), _stash.text_italic(tips[idx])))
    except KeyboardInterrupt:
        print("\nOperation interrupted by user.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print("totd: error: %s" % str(e), file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main(sys.argv[1:])
