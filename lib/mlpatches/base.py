# -*- coding: utf-8 -*-
"""This module contains the base class for patches."""

import sys
import os
import importlib.machinery
import importlib.util

from stashutils.core import get_stash

SKIP = "<skip>'  # indicate that this patch should be skipped.'"

_stash = get_stash()


def load_source(modname, filename):
    loader = importlib.machinery.SourceFileLoader(modname, filename)
    spec = importlib.util.spec_from_file_location(modname, filename, loader=loader)
    module = importlib.util.module_from_spec(spec)
    # The module is always executed and not cached in sys.modules.
    # Uncomment the following line to cache the module.
    # sys.modules[module.__name__] = module
    loader.exec_module(module)
    return module


class IncompatiblePatch(Exception):
    """raised when a patch is incompatible."""

    pass


class BasePatch(object):
    """
    Baseclass for other patches.
    This class also keeps track wether patches are enabled or not.
    Subclasses should call BasePatch.__init__(self) and should
    overwrite do_enable() and do_disable().
    Subclasses may also overwrite self.dependencies with a list of patches which need to be enabled before the patch will be enabled.
    """

    PY2 = True  # Python 2 compatibility
    PY3 = False  # Python 3 compatibility
    dependencies = []

    def __init__(self):
        self.enabled = False

    def enable(self):
        """enable the patch."""
        for patch in self.dependencies:
            patch.enable()
        if not self.enabled:
            pyv = sys.version_info[0]
            if pyv == 2:
                if self.PY2 == SKIP:
                    return  # skip patch activation
                if not self.PY2:
                    raise IncompatiblePatch("Python 2 not supported!")
            if pyv == 3:
                if self.PY3 == SKIP:
                    return  # skip patch activation
                if not self.PY3:
                    raise IncompatiblePatch("Python 3 not supported!")
            self.pre_enable()
            self.do_enable()
            self.enabled = True

    def disable(self):
        """disable the patch. Do NOT disable dependencies."""
        if self.enabled:
            self.do_disable()
            self.enabled = False

    def do_enable(self):
        """this should be overwritten in subclasses and apply the patch."""
        pass

    def do_disable(self):
        """This should be overwritten in subclasses and remove the patch."""
        pass

    def pre_enable(self):
        """this will be called between enable() and do_enable()."""
        pass


class FunctionPatch(BasePatch):
    """
    This is a baseclass for patches replacing functions or classes.
    Subclasses should redefine self.module and self.function.
    'module' should be a string with the name of the module to load.
    'function' should be a string with the name of the function to replace.
    'replacement' should be the replacement.
    """

    module = None
    function = None
    replacement = None

    def __init__(self):
        BasePatch.__init__(self)
        self.old = None

    def do_enable(self):
        if (
            (self.function is None)
            or (self.module is None)
            or (self.replacement is None)
        ):
            raise ValueError("Invalid Patch definition!")

        if self.module not in sys.modules:
            # Use importlib.util.find_spec to locate the module
            spec = importlib.util.find_spec(self.module)

            if spec is None:
                raise ImportError(f"Module '{self.module}' not found.")

            # Create the module object from the specification
            module = importlib.util.module_from_spec(spec)

            # Register the module in sys.modules
            sys.modules[self.module] = module

            # Execute the module's code to populate its namespace
            spec.loader.exec_module(module)
        else:
            # If the module is already loaded, get it from sys.modules
            module = sys.modules[self.module]

        self.old = getattr(module, self.function)
        setattr(module, self.function, self.replacement)

    def do_disable(self):
        module = sys.modules[self.module]
        if self.old is not None:
            setattr(module, self.function, self.old)


class ModulePatch(BasePatch):
    """
    This is a baseclass for patches replacing/adding modules.
    Subclasses should overwrite self.relpath to point to the the module.
    self.relpath is relative to self.BASEPATH.
    Subclasses may also overwrite self.name with the module name.
    Otherwise, self.name = relpath
    """

    name = None
    relpath = None
    BASEPATH = os.path.join(os.path.dirname(__file__), "modules")

    def __init__(self):
        BasePatch.__init__(self)
        if self.relpath is None:
            raise ValueError("Invalid Patch definition!")
        self.path = os.path.join(self.BASEPATH, self.relpath)
        if self.name is None:
            self.name = self.relpath

    def do_enable(self):
        if self.name in sys.modules:
            del sys.modules[self.name]
        with open(self.path, "r") as f:
            nmod = load_source(self.name, self.path, f)
        sys.modules[self.name] = nmod

    def do_disable(self):
        if self.name in sys.modules:
            del sys.modules[self.name]


class PatchGroup(BasePatch):
    """
    This is a baseclass for a group of patches.
    Subclasses should overwrite self.patches.
    """

    patches = []

    @property
    def enabled(self):
        """checks wether all patches of this group are enabled."""
        return all([p.enabled for p in self.patches]) and len(self.patches) > 0

    @enabled.setter
    def enabled(self, value):
        # no-op, but required
        pass

    def enable(self):
        # we need to overwrite enable() because
        # the patches should check wether they are already enabled
        self.pre_enable()
        self.do_enable()

    def disable(self):
        # see enable
        self.do_disable()

    def do_enable(self):
        for p in self.patches:
            p.enable()

    def do_disable(self):
        for p in self.patches:
            p.disable()


class VariablePatchGroup(PatchGroup):
    """
    A patchgroup which patches are passed to __init__().
    This allows a variable definition on import.
    """

    def __init__(self, patches):
        PatchGroup.__init__(self)
        self.patches = patches
