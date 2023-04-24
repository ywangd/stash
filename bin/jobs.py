# -*- coding: utf-8 -*-
"""
List all jobs that are currently running.
"""
from __future__ import print_function
import sys
import argparse
import threading


def main(args):
    ap = argparse.ArgumentParser()
    ap.parse_args(args)

    current_worker = threading.current_thread()

    _stash = globals()['_stash']
    """:type : StaSh"""

    for worker in _stash.get_workers():
        if worker.job_id != current_worker.job_id:
            print(worker)


if __name__ == '__main__':
    main(sys.argv[1:])
