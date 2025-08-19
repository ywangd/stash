# -*- coding: utf-8 -*-
"""Print the last 10 lines of the given files."""

import argparse
import time
import sys
import fileinput


def tail_f(f, wait_sec):
    while True:
        line = f.readline()
        if line:
            yield line
        else:
            # print('!!READ NOTHING!!')
            time.sleep(wait_sec)


_first_file = True


def write_header(fname):
    global _first_file
    header_fmt = "{}==> {} <==\n"
    print(header_fmt.format("" if _first_file else "\n", fname), end="")
    _first_file = False


def main(args):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "-c",
        "--bytes",
        default="",
        type=str,
        metavar="K",
        help="""output the last K bytes; or -c +K starting with the Kth""",
    )
    p.add_argument(
        "-f", "--follow", action="store_true", help="""follow specified files"""
    )
    p.add_argument(
        "-n",
        "--lines",
        default="10",
        type=str,
        metavar="K",
        help="""print the last K lines instead of 10;
                   or use -n +K to print lines starting with the Kth""",
    )
    p.add_argument(
        "-q",
        "--quiet",
        "--silent",
        action="store_true",
        help="never print headers for each file",
    )
    p.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="always print headers for each file",
    )
    p.add_argument(
        "-s",
        "--sleep-interval",
        type=float,
        default=1.0,
        help="with -f, sleep for approximately N seconds (default 1.0) between iterations.",
    )
    p.add_argument("files", action="store", nargs="*", help="files to print")
    ns = p.parse_args(args)

    status = 0

    if len(ns.files) == 0:
        ns.files = ["-"]

    if ns.follow and "-" in ns.files:
        print("tail: warning: following stdin indefinitely is ineffective")

    if ns.bytes:
        use_bytes = True
        if ns.bytes[0] == "+":
            from_start = True
        else:
            from_start = False
        count = abs(int(ns.bytes))  # '-n -3' is equivalent to '-n 3'
    else:
        use_bytes = False
        if ns.lines[0] == "+":
            from_start = True
        else:
            from_start = False
        count = abs(int(ns.lines))  # '-n -3' is equivalent to '-n 3'

    try:
        for i, fname in enumerate(ns.files):
            if ns.verbose or (len(ns.files) > 1 and not ns.quiet):
                write_header(fname if fname != "-" else "standard input")

            try:
                if fname == "-":
                    f = sys.stdin
                else:
                    f = open(fname)

                buf = []
                j = -1
                while True:
                    j += 1
                    if use_bytes:
                        line = f.read(1)
                    else:
                        line = f.readline()
                    if not line:
                        break

                    buf.append(line)
                    if from_start:
                        if j >= count - 1:
                            break
                    elif len(buf) > count:
                        del buf[0]

                for item in buf:
                    print(item, end="")

                if i == len(ns.files) - 1 and ns.follow:
                    for line in tail_f(f, ns.sleep_interval):
                        print(line, end="")
                        sys.stdout.flush()
            finally:
                if fname != "-":
                    f.close()

    except Exception as e:
        print("tail :%s" % str(e))
        status = 1
    finally:
        fileinput.close()

    sys.exit(status)


if __name__ == "__main__":
    main(sys.argv[1:])
