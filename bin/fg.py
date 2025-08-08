# -*- coding: utf-8 -*-
"""
Bring a background job to foreground.
"""

import sys
import argparse
import threading


def main(args):
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "job_id", nargs="?", type=int, help="ID of a running background job"
    )
    ns = ap.parse_args(args)

    _stash = globals()["_stash"]
    worker_registry = _stash.runtime.worker_registry

    if ns.job_id is None:
        worker = worker_registry.get_first_bg_worker()
    else:
        worker = worker_registry.get_worker(ns.job_id)

    if worker is None:
        print(
            "no background job running"
            + (" with id {}".format(ns.job_id) if ns.job_id else "")
        )
        return

    def f():
        _stash.runtime.push_to_foreground(worker)

    t = threading.Timer(1.0, f)
    print("pushing job {} to foreground ...".format(worker.job_id))
    t.start()


if __name__ == "__main__":
    main(sys.argv[1:])
