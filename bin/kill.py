# -*- coding: utf-8 -*-
"""
Terminate a running job.
"""
from __future__ import print_function
import sys
import argparse
import time


def main(args):
    ap = argparse.ArgumentParser()
    ap.add_argument('job_ids', nargs='+', type=int, help='ID of a running job')

    ns = ap.parse_args(args)

    _stash = globals()['_stash']
    """:type : StaSh"""

    for job_id in ns.job_ids:
        if job_id in _stash.runtime.worker_registry:
            print('killing job {} ...'.format(job_id))
            worker = _stash.runtime.worker_registry.get_worker(job_id)
            worker.kill()
            time.sleep(1)

        else:
            print('error: no such job with id: {}'.format(job_id))
            break


if __name__ == '__main__':
    main(sys.argv[1:])
