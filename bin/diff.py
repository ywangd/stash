#!/usr/bin/env python

import sys
import os
import json
import argparse
from pathlib import Path
from typing import Sequence, Any

import pytz

from datetime import datetime
from difflib import unified_diff

try:
    import console  # type: ignore[import-not-found]
except ImportError:
    console = None

_stash = globals().get("_stash")

# Define ANSI color codes
ANSI_GREEN = "\x1b[92m"  # For added lines (+)
ANSI_RED = "\x1b[91m"  # For removed lines (-)
ANSI_RESET = "\x1b[0m"  # To reset the color


def argue(args: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("lhs", type=Path)
    parser.add_argument("rhs", type=Path)
    ns = parser.parse_args(args)
    if ns.verbose:
        json.dump(vars(ns), sys.stderr, indent=4)
    return ns


def sn(x: Any) -> str:
    return "%s\n" % x


def modified(f: Path) -> str:
    timestamp = os.path.getmtime(f)
    utc_dt = datetime.fromtimestamp(timestamp, tz=pytz.utc)
    sydney_tz = pytz.timezone("Australia/Sydney")
    sydney_dt = utc_dt.astimezone(sydney_tz)
    return sydney_dt.strftime("%Y-%m-%d %H:%M:%S")


def print_line(line: str) -> None:
    if _stash:
        if line.startswith("+"):
            line = _stash.text_color(line, "green")
        elif line.startswith("-"):
            line = _stash.text_color(line, "red")
    elif console:
        # Use the 'console' module if available
        if line.startswith("+"):
            console.set_color(0, 1, 0)
        elif line.startswith("-"):
            console.set_color(0, 0, 1)
        else:
            console.set_color(1, 1, 1)
    else:
        # Use ANSI escape codes if 'console' is not available
        if line.startswith("+"):
            line = ANSI_GREEN + line
        elif line.startswith("-"):
            line = ANSI_RED + line
        else:
            line = ANSI_RESET + line

    sys.stdout.write(line)


def diff(lhs: Path, rhs: Path) -> None:
    if not lhs.is_file():
        sys.stderr.write("%s not a file\n" % lhs)
        sys.exit(1)
    if rhs.is_dir():
        # CORRECT: Use the / operator to join the Path objects
        rhs = rhs / lhs.name
    if not rhs.is_file():
        sys.stderr.write("%s not a file\n" % rhs)
        sys.exit(1)

    with open(lhs, "r", encoding="utf-8") as fp:
        flhs = fp.readlines()

    with open(rhs, "r", encoding="utf-8") as fp:
        frhs = fp.readlines()

    diffs = unified_diff(
        flhs,
        frhs,
        fromfile=lhs.as_posix(),
        tofile=rhs.as_posix(),
        fromfiledate=modified(lhs),
        tofiledate=modified(rhs),
    )
    for line in diffs:
        print_line(line)


def main(args: Sequence[str]) -> None:
    if _stash:
        _stash("clear")
    elif console:
        console.clear()
    else:
        sys.stdout.write("\x1b[H\x1b[2J")
    ns = argue(args)
    try:
        diff(ns.lhs, ns.rhs)
    except FileNotFoundError:
        sys.stderr.write("%s not found\n" % ns.lhs)
    except KeyboardInterrupt:
        sys.stderr.write("Interrupted by user\n")
    except Exception as e:
        sys.stderr.write(f"diff: error: {e}\n")
    return


if __name__ == "__main__":
    main(sys.argv[1:])
