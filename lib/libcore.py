import os
import fileinput

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
        collapsed = path

    return "~" if collapsed == "." else os.path.join("~", collapsed)


def input_stream(files=()):
    """ Handles input files similar to fileinput.
    The advantage of this function is it recovers from errors if one
    file is invalid and proceed with the next file
    """
    fileinput.close()
    try:
        if not files:
            for line in fileinput.input(files):
                yield line, 'STDIN', fileinput.filelineno()

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


