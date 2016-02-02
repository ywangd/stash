# coding=utf-8
""" When multiple scripts running in parallel in different threads.
Each of them requires its own copy of modules and module variables,
e.g. sys.argv, os.environ, etc.
Each script has its own copy and can make changes to its own copy
without affecting other script's environment.

The module proxy does this in a hackish way by replacing the magic
__import__ and reload functions to intercept import and reload
calls and return custom modules if calls are from worker threads.

NOTE: Even when the sys module is mocked, its io properties (e.g. stdout)
are not recognized by print, i.e. all prints still go to the console
page. So shiowrapper is created to intercept all IO calls when stash is
running and dispatch them based on the running thread.
"""
import imp
import __builtin__
import threading
import logging

from .shthreads import ShBaseThread

logger = logging.getLogger('Stash.ImportProxy')

_DEBUG = False
_ENABLED = False
_INTERCEPT_MODULES = ('os', 'sys')

# A mock module by delegating the real one
_MOCK_CODE_TEMPLATE = """
from {} import *
ASDF='HAHA'
"""


def _make_mock_module(name):
    """ make a mock module for the given name by delegating
    the real module with the same name, e.g. sys.
    """
    if _DEBUG:
        logger.debug('making mock module: {}'.format(name))
    mock_module = imp.new_module(name)
    exec _MOCK_CODE_TEMPLATE.format(name) in mock_module.__dict__
    return mock_module

# Template mock modules
_mock_modules = {
    'sys': _make_mock_module('sys'),
    'os': _make_mock_module('os'),
}

# Save the original import and reload functions
__baseimport = __builtin__.__baseimport if hasattr(__builtin__, '__baseimport') \
    else __builtin__.__import__
__basereload = __builtin__.__basereload if hasattr(__builtin__, '__basereload') \
    else __builtin__.reload


def __shimport(name, *args, **kwargs):
    """
    Custom import function
    """
    current_thread = threading.currentThread()
    if _DEBUG:
        logger.debug('importing {}, {}({})'.format(
            name, current_thread.name, current_thread.ident))

    # Custom import logic for modules required to be intercepted
    if name in _INTERCEPT_MODULES and isinstance(current_thread, ShBaseThread):
        if _DEBUG:
            logger.debug('returning mock: {}'.format(name))

        if name not in current_thread.mock_modules:
            mock_module = imp.new_module(name)  # new mock module
            # populate the new mock module with the template mock
            mock_module.__dict__.update(_mock_modules[name].__dict__)
            # Save the mock for future faster reload
            current_thread.mock_modules[name] = mock_module

        # Update for the specific thread
        current_thread.mock_modules[name].__dict__.update(
            current_thread.state.__dict__[name])

        return current_thread.mock_modules[name]

    else:  # delegate to normal import
        return __baseimport(name, *args, **kwargs)

def __shreload(m):
    """
    Custom reload function
    """
    current_thread = threading.currentThread()
    if _DEBUG:
        logger.debug('reloading {}, {}({})'.format(
            m.__name__, current_thread.name, current_thread.ident))

    # Custom reload logic for modules required to be intercepted
    if m.__name__ in _INTERCEPT_MODULES and isinstance(current_thread, ShBaseThread):
        if _DEBUG:
            logger.debug('returning mock: {}'.format(m.__name__))
        if m.__name__ not in current_thread.mock_modules:
            raise NameError("name '{}' is not defined".format(m.__name__))
        else:
            return current_thread.mock_modules[m.__name__]

    else: # delegate to normal reload
        return __basereload(m)


def set_debug(state=True):
    """
    Turn on debug mode for logging messages.
    """
    global _DEBUG
    _DEBUG = bool(state)

def enable():
    """
    Enable import proxy.
    """
    global _ENABLED
    if not _ENABLED:
        __builtin__.__import__ = __shimport
        __builtin__.reload = __shreload
        _ENABLED = True

def disable():
    """
    Disable import proxy
    """
    global _ENABLED
    if _ENABLED:
        __builtin__.__import__ = __baseimport
        __builtin__.reload = __basereload
        _ENABLED = False
