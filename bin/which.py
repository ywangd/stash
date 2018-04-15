""" Locate a command script in BIN_PATH. No output if command is not found.
"""


def main(command):
    rt = globals()['_stash'].runtime
    try:
        filename = rt.find_script_file(command)
        print(filename)
    except Exception:
        pass


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('command', help='name of the command to be located')
    ns = ap.parse_args()
    main(ns.command)
