"""
Quit a shell.
"""
import argparse


_stash = globals()["_stash"]


def logout(n):
    """
    Quit StaSh
    :param n: exitcode for the shell (not implemented)
    :type n: int
    """
    import threading
    t = threading.Thread(target=_stash.close, name="close thread")
    t.daemon = True
    t.start()
    


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Quits a shell")
    parser.add_argument("n", nargs="?", default=0, type=int, help="exit the shell with this code. Not implemented.")
    ns = parser.parse_args()
    logout(ns.n)
