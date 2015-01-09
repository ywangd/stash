import os

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