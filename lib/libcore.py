# -*- coding: utf-8 -*-
import os
import fileinput

try:
    unicode
except NameError:
    unicode = str
    
    
def abbreviate(filename,relativeTo='.'):
    result = collapseuser(filename)
    if result.startswith('~'):
        return result
    return os.path.relpath(filename,relativeTo)


def collapseuser(path):
    """Reverse of os.path.expanduser: return path relative to ~, if
    such representation is meaningful. If path is not ~ or a
    subdirectory, the absolute path will be returned.
    """
    path = os.path.abspath(unicode(path))
    home = os.path.expanduser("~")
    if os.path.exists(os.path.expanduser("~/Pythonista.app")):
        althome = os.path.dirname(os.path.realpath(os.path.expanduser("~/Pythonista.app")))
    else:
        althome = home

    if path.startswith(home):
        collapsed = os.path.relpath(path, home)
    elif path.startswith(althome):
        collapsed = os.path.relpath(path, althome)
    else:
        return path

    return "~" if collapsed == "." else os.path.join("~", collapsed)


def get_lan_ip():
    try:
        from objc_util import ObjCClass
        NSHost = ObjCClass('NSHost')
        addresses = []
        for address in NSHost.currentHost().addresses():
            address = str(address)
            if 48 <= ord(address[0]) <= 57 and address != '127.0.0.1':
                addresses.append(address)
        return '   '.join(addresses)

    except ImportError:
        return ''


def input_stream(files=()):
    """ Handles input files similar to fileinput.
    The advantage of this function is it recovers from errors if one
    file is invalid and proceed with the next file
    """
    fileinput.close()
    try:
        if not files:
            for line in fileinput.input(files):
                yield line, '', fileinput.filelineno()

        else:
            while files:
                thefile = files.pop(0)
                try:
                    for line in fileinput.input(thefile):
                        yield line, fileinput.filename(), fileinput.filelineno()
                except IOError as e:
                    yield None, fileinput.filename(), e
    finally:
        fileinput.close()


def sizeof_fmt(num):
    """
    Return a human readable string describing the size of something.
    :param num: the number in machine-readble form
    :type num: int
    :param base: base of each unit (e.g. 1024 for KiB -> MiB)
    :type base: int
    :param suffix: suffix to add. By default, the string returned by sizeof_fmt() does not contain a suffix other than 'K', 'M', ...
    :type suffix: str
    """
    for unit in ['B', 'KiB', 'MiB', 'GiB']:
        if num < 1024:
            return "%3.1f%s" % (num, unit)
        num /= 1024.0
    return "%3.1f%s" % (num, 'Ti')
