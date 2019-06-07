# -*- coding: utf-8 -*-
"""common methods"""
import os


def get_stash_dir():
    """
    Returns the StaSh root directory, detected from this file.
    :return: the StaSh root directory
    :rtype: str
    """
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    """
    The main function.
    """
    print("StaSh root directory: {}".format(get_stash_dir()))


if __name__ == "__main__":
    main()
