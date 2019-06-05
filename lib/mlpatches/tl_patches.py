# -*- coding: utf-8 -*-
"""patches for making some vars thread-local"""
import threading
import copy
from mlpatches import base


class ThreadLocalVar(object):
    """creates a proxy to a thread-local version of passee var."""
    # todo: maybe add lock?

    def __init__(self, var):
        self.__var = var
        self.__local = threading.local()
        self.__setattr__ = self.__setattr_  # set __settattr__ here

    def __getattr__(self, name):
        try:
            v = self.__local.var
        except AttributeError:
            v = self.__local.var = copy.deepcopy(self.__var)
        return getattr(v, name)

    def __setattr_(self, name, value):  # keep missing "_"
        try:
            v = self.__local.var
        except AttributeError:
            v = self.__local.var = copy.deepcopy(self.__var)
        return setattr(v, name, value)

    def __delattr__(self, name):
        try:
            v = self.__local.var
        except AttributeError:
            v = self.__local.var = copy.deepcopy(self.__var)
        return delattr(v, name)

    def __del__(self):
        try:
            del self.__local.var
        except AttributeError:
            pass


# define patches

class ThreadLocalArgv(base.FunctionPatch):
    """Patches sys.argv to be thread-local."""
    PY2 = True
    PY3 = True
    module = "sys"
    function = "argv"
    replacement = ThreadLocalVar([])


# create patch instances
TL_ARGV_PATCH = ThreadLocalArgv()
