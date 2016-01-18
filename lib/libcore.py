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


def get_lan_ip():
    try:
        from objc_util import ObjCClass
        NSHost = ObjCClass('NSHost')
        for address in NSHost.currentHost().addresses():
            address = str(address)
            if 48 <= ord(address[0]) <= 57 and address != '127.0.0.1':
                return address

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


def install_module_from_github(username, package_name, version, append_version=True):
    """
    Download and install a module from github using its release zip file.
    The module is install in $STASH_ROOT/lib to separate from system
    paths. Thus the module is only usable from within StaSh.
    :param username:
    :param package_name:
    :param version:
    :return:
    """
    cmd_string = """
    echo Installing {1} 1.16.0 ...
    wget https://github.com/{0}/{1}/archive/v{2}.zip -o $TMPDIR/{1}.zip
    mkdir $TMPDIR/{1}_src
    unzip $TMPDIR/{1}.zip -d $TMPDIR/{1}_src
    rm -f $TMPDIR/{1}.zip
    mv $TMPDIR/{1}_src/{1} $STASH_ROOT/lib/{1}{3}
    rm -rf $TMPDIR/{1}_src
    echo Done
    """.format(username,
               package_name,
               version,
               '_' + version.replace('.', '_') if append_version else ''
    )
    globals()['_stash'](cmd_string)
