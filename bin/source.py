"""
Read and execute commands from a shell script in the current environment.

usage: source.py [-h] file [args [args ...]]

positional arguments:
  file        file to be sourced
  args        arguments to the file being sourced

optional arguments:
  -h, --help  show this help message and exit
"""

import sys
from argparse import ArgumentParser

def main(args):
    ap = ArgumentParser(description="Read and execute commands from a shell script in the current environment")
    ap.add_argument('file', action="store", help='file to be sourced')
    ap.add_argument('args', nargs='*', help='arguments to the file being sourced')
    ns = ap.parse_args(args)

    _stash = globals()['_stash']
    rt = _stash.runtime

    # The special thing about source is it persists any environmental changes
    # in the sub-shell through the parent one. Otherwise, we can use
    # exec_sh_file to do the job.

    for i, arg in enumerate([ns.file] + ns.args):
        rt.enclosing_envars[str(i)] = arg
    rt.enclosing_envars['#'] = len(ns.args)
    rt.enclosing_envars['@'] = '\t'.join(ns.args)

    try:
        with open(ns.file) as ins:
            worker = rt.run(ins.readlines(),
                            persist_envars=True,
                            persist_aliases=True,
                            persist_cwd=True)
            worker.join()
    except IOError as e:
        print '%s: %s' % (e.filename, e.strerror)
    except Exception as e:
        print 'error: %s' % str(e)
    finally:
        for i in range(len(ns.args) + 1):
            rt.envars.pop(str(i))
        rt.envars.pop('#')
        rt.envars.pop('@')

if __name__ == '__main__':
    main(sys.argv[1:])

