"""This module defines functions to interact with stash extensions."""
import os
import shutil

from stash.system.shcommon import _STASH_EXTENSION_BIN_PATH as EBP
from stash.system.shcommon import _STASH_EXTENSION_MAN_PATH as EMP
from stash.system.shcommon import _STASH_EXTENSION_FSI_PATH as EFP
from stash.system.shcommon import _STASH_EXTENSION_PATCH_PATH as EPP

from stashutils.core import load_from_dir

from six import text_type, binary_type


# alias load_from_dir (so you can access it trough this namespace)
load_from_dir = load_from_dir


def create_file(dest, content):
    """
    creates a file at dest with content.
    If content is a string or unicode, use it as the content.
    Otherwise, use content.read() as the content.
    """
    if not isinstance(content, (binary_type, text_type)):
        content = content.read()
    parent = os.path.dirname(dest)
    if not os.path.exists(parent):
        os.makedirs(parent)
    with open(dest, "wb") as f:
        f.write(content)
    return dest


def create_page(name, content):
    """
    creates a manpage with name filled with content.
    If content is a list or tuple, instead create a dir and fill it with pages
    created from the elements of this list.
    The list should consist of tuples of (ending, content)
    """
    path = os.path.join(EMP, name)
    if isinstance(content, (list, tuple)):
        # create a bunch of pages
        if os.path.exists(path):
            shutil.rmtree(path)
        os.mkdir(path)
        for n, element in enumerate(content, 1):
            ending, elementcontent = element
            pagename = "{b}/page_{n}.{e}".format(n=n, e=ending, b=path)
            create_page(pagename, elementcontent)
        return path
    else:
        return create_file(path, content)


def create_command(name, content):
    """creates a script named name filled with content"""
    path = os.path.join(EBP, name)
    return create_file(path, content)


def create_fsi_file(name, content):
    """creates a fsi extension named name filled with content"""
    path = os.path.join(EFP, name)
    return create_file(path, content)


def create_patch_file(name, content):
    """creates a patch extension named name filled with content"""
    path = os.path.join(EPP, name)
    return create_file(path, content)
