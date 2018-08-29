# -*- coding: utf-8 -*-
"""
The Control, Escape and Graphics are taken from pyte (https://github.com/selectel/pyte)
"""
import os
import sys
import platform
import functools
import threading
import ctypes
from itertools import chain

import six


IN_PYTHONISTA = sys.executable.find('Pythonista') >= 0

if IN_PYTHONISTA:
    import plistlib

    _properties = plistlib.readPlist(os.path.join(os.path.dirname(sys.executable), 'Info.plist'))
    PYTHONISTA_VERSION = _properties['CFBundleShortVersionString']
    PYTHONISTA_VERSION_LONG = _properties['CFBundleVersion']

    if PYTHONISTA_VERSION < '3.0':
        python_capi = ctypes.pythonapi
    else:
        # The default pythonapi always points to Python 3 in Pythonista 3
        if six.PY3:
            python_capi = ctypes.pythonapi
        else:
             # We need to load the Python 2 API manually
            try:
                python_capi = ctypes.PyDLL(
                os.path.join(os.path.dirname(sys.executable),
                             'Frameworks/Py2Kit.framework/Py2Kit'))
            except OSError:
                python_capi = ctypes.PyDLL(
                os.path.join(os.path.dirname(sys.executable),
                             'Frameworks/PythonistaKit.framework/PythonistaKit'))
        
else:
    PYTHONISTA_VERSION = '0.0'
    PYTHONISTA_VERSION_LONG = '000000'
    python_capi = ctypes.pythonapi

platform_string = platform.platform()

ON_IPAD = platform_string.find('iPad') >= 0
ON_IOS_8 = platform_string.split('-')[1].startswith('14')
M_64 = platform_string.find('64bit') != -1

CTRL_KEY_FLAG = (1 << 18)  # Control key for keyCommands
CMD_KEY_FLAG = (1 << 20)  # Command key

_STASH_ROOT = os.path.realpath(os.path.abspath(
    os.path.dirname(os.path.dirname(__file__))))
_STASH_CONFIG_FILES = ('.stash_config', 'stash.cfg')
_STASH_HISTORY_FILE = '.stash_history'

# directory for stash extensions
_STASH_EXTENSION_PATH = os.path.abspath(
	os.path.join(os.getenv("HOME"), "Documents", "stash_extensions"),
	)
# directory for stash bin extensions
_STASH_EXTENSION_BIN_PATH = os.path.join(_STASH_EXTENSION_PATH, "bin")
# directory for stash man extensions
_STASH_EXTENSION_MAN_PATH = os.path.join(_STASH_EXTENSION_PATH, "man")
# directory for stash FSI extensions
_STASH_EXTENSION_FSI_PATH = os.path.join(_STASH_EXTENSION_PATH, "fsi")
# directory for stash patch extensions
_STASH_EXTENSION_PATCH_PATH = os.path.join(_STASH_EXTENSION_PATH, "patches")
# list of directories outside of _STASH_ROOT, used for simple mkdir
_EXTERNAL_DIRS = [
	_STASH_EXTENSION_PATH,
	_STASH_EXTENSION_BIN_PATH,
	_STASH_EXTENSION_MAN_PATH,
	_STASH_EXTENSION_FSI_PATH,
	_STASH_EXTENSION_PATCH_PATH,
	]

# Python 3 or not Python 3
PY3 = six.PY3

# Save the true IOs
if IN_PYTHONISTA:
    # The stdio catchers recreation is copied from code written by @dgelessus
    # https://forum.omz-software.com/topic/1946/pythonista-1-6-beta/167
    # In pythonista beta 301006, _outputcapture was replaced with pykit_io
    try:
        import _outputcapture
    except ImportError:
        import pykit_io
        class _outputcapture(object):
            ReadStdin=pykit_io.read_stdin
            CaptureStdout=pykit_io.write_stdout
            CaptureStderr=pykit_io.write_stderr
        				
    if sys.stdin.__class__.__name__ == 'StdinCatcher':
        _SYS_STDIN = sys.__stdin__ = sys.stdin
    elif sys.__stdin__.__class__.__name__ == 'StdinCatcher':
        _SYS_STDIN = sys.__stdin__
    else:
        class StdinCatcher(object):
            def __init__(self):
                self.encoding = 'utf8'

            def read(self, limit=-1):
                return _outputcapture.ReadStdin(limit)

            def readline(self):
                return _outputcapture.ReadStdin()


        _SYS_STDIN = StdinCatcher()

    if sys.stdout.__class__.__name__ == 'StdoutCatcher':
        _SYS_STDOUT = sys.__stdout__ = sys.stdout
    elif sys.__stdout__.__class__.__name__ == 'StdoutCatcher':
        _SYS_STDOUT = sys.__stdout__
    else:
        class StdoutCatcher(object):
            def __init__(self):
                self.encoding = 'utf8'

            def flush(self):
                pass

            def write(self, s):
                if isinstance(s, str):
                    _outputcapture.CaptureStdout(s)
                elif isinstance(s, six.text_type):
                    _outputcapture.CaptureStdout(s.encode('utf8'))

            def writelines(self, lines):
                self.write(''.join(lines))


        _SYS_STDOUT = StdoutCatcher()

    if sys.stderr.__class__.__name__ == 'StderrCatcher':
        _SYS_STDERR = sys.__stderr__ = sys.stderr
    elif sys.stderr.__class__.__name__ == 'StderrCatcher':
        _SYS_STDERR = sys.__stderr__
    else:
        class StderrCatcher(object):
            def __init__(self):
                self.encoding = 'utf8'

            def flush(self):
                pass

            def write(self, s):
                if isinstance(s, str):
                    _outputcapture.CaptureStderr(s)
                elif isinstance(s, six.text_type):
                    _outputcapture.CaptureStderr(s.encode('utf8'))

            def writelines(self, lines):
                self.write(''.join(lines))

        _SYS_STDERR = StderrCatcher()
else:
    _SYS_STDOUT = sys.stdout
    _SYS_STDERR = sys.stderr
    _SYS_STDIN = sys.stdin

_SYS_PATH = sys.path
_OS_ENVIRON = os.environ


def is_binary_file(filename, nbytes=1024):
    """
    An approximate way to tell whether a file is binary.
    :param str filename: The name of the file to be tested.
    :param int nbytes: number of bytes to read for test
    :return:
    """
    with open(filename, 'rb') as ins:
        for c in ins.read(nbytes):
            if isinstance(c, six.integer_types):
                oc = c
            else:
                oc = ord(c)
            if 127 < oc < 256 or (oc < 32 and oc not in (9, 10, 13)):
                return True
        else:
            return False


def sh_delay(func, nseconds):
    t = threading.Timer(nseconds, func)
    t.start()
    return t


def sh_background(name=None):
    def wrap(func):
        @functools.wraps(func)
        def wrapped_func(*args, **kwargs):
            t = threading.Thread(name=name, target=func, args=args, kwargs=kwargs)
            t.start()
            return t

        return wrapped_func

    return wrap


class ShFileNotFound(Exception):
    pass


class ShIsDirectory(Exception):
    pass


class ShNotExecutable(Exception):
    def __init__(self, filename):
        super(Exception, self).__init__('{}: not executable\n'.format(filename))


class ShSingleExpansionRequired(Exception):
    pass


class ShEventNotFound(Exception):
    pass


class ShBadSubstitution(Exception):
    pass


class ShSyntaxError(Exception):
    pass


class ShInternalError(Exception):
    pass


class Control(object):
    """
        pyte.control
        ~~~~~~~~~~~~

        This module defines simple control sequences, recognized by
        :class:`~pyte.streams.Stream`, the set of codes here is for
        ``TERM=linux`` which is a superset of VT102.

        :copyright: (c) 2011-2013 by Selectel, see AUTHORS for details.
        :license: LGPL, see LICENSE for more details.
    """

    #: *Space*: Not suprisingly -- ``" "``.
    SP = u" "

    #: *Null*: Does nothing.
    NUL = u"\u0000"

    #: *Bell*: Beeps.
    BEL = u"\u0007"

    #: *Backspace*: Backspace one column, but not past the beginning of the
    #: line.
    BS = u"\u0008"

    #: *Horizontal tab*: Move cursor to the next tab stop, or to the end
    #: of the line if there is no earlier tab stop.
    HT = u"\u0009"

    #: *Linefeed*: Give a line feed, and, if :data:`pyte.modes.LNM` (new
    #: line mode) is set also a carriage return.
    LF = u"\n"
    #: *Vertical tab*: Same as :data:`LF`.
    VT = u"\u000b"
    #: *Form feed*: Same as :data:`LF`.
    FF = u"\u000c"

    #: *Carriage return*: Move cursor to left margin on current line.
    CR = u"\r"

    #: *Shift out*: Activate G1 character set.
    SO = u"\u000e"

    #: *Shift in*: Activate G0 character set.
    SI = u"\u000f"

    #: *Cancel*: Interrupt escape sequence. If received during an escape or
    #: control sequence, cancels the sequence and displays substitution
    #: character.
    CAN = u"\u0018"
    #: *Substitute*: Same as :data:`CAN`.
    SUB = u"\u001a"

    #: *Escape*: Starts an escape sequence.
    ESC = u"\u001b"

    #: *Delete*: Is ignored.
    DEL = u"\u007f"

    #: *Control sequence introducer*: An equivalent for ``ESC [``.
    CSI = u"\u009b"


class Escape(object):
    """
        pyte.escape
        ~~~~~~~~~~~

        This module defines both CSI and non-CSI escape sequences, recognized
        by :class:`~pyte.streams.Stream` and subclasses.

        :copyright: (c) 2011-2013 by Selectel, see AUTHORS for details.
        :license: LGPL, see LICENSE for more details.
    """

    #: *Reset*.
    RIS = u"c"

    #: *Index*: Move cursor down one line in same column. If the cursor is
    #: at the bottom margin, the screen performs a scroll-up.
    IND = u"D"

    #: *Next line*: Same as :data:`pyte.control.LF`.
    NEL = u"E"

    #: Tabulation set: Set a horizontal tab stop at cursor position.
    HTS = u"H"

    #: *Reverse index*: Move cursor up one line in same column. If the
    #: cursor is at the top margin, the screen performs a scroll-down.
    RI = u"M"

    #: Save cursor: Save cursor position, character attribute (graphic
    #: rendition), character set, and origin mode selection (see
    #: :data:`DECRC`).
    DECSC = u"7"

    #: *Restore cursor*: Restore previously saved cursor position, character
    #: attribute (graphic rendition), character set, and origin mode
    #: selection. If none were saved, move cursor to home position.
    DECRC = u"8"

    # "Percent" escape sequences.
    # ---------------------------

    #: *Select default (ISO 646 / ISO 8859-1)*.
    DEFAULT = u"@"

    #: *Select UTF-8*.
    UTF8 = u"G"

    #: *Select UTF-8 (obsolete)*.
    UTF8_OBSOLETE = u"8"

    # "Sharp" escape sequences.
    # -------------------------

    #: *Alignment display*: Fill screen with uppercase E's for testing
    #: screen focus and alignment.
    DECALN = u"8"

    # ECMA-48 CSI sequences.
    # ---------------------

    #: *Insert character*: Insert the indicated # of blank characters.
    ICH = u"@"

    #: *Cursor up*: Move cursor up the indicated # of lines in same column.
    #: Cursor stops at top margin.
    CUU = u"A"

    #: *Cursor down*: Move cursor down the indicated # of lines in same
    #: column. Cursor stops at bottom margin.
    CUD = u"B"

    #: *Cursor forward*: Move cursor right the indicated # of columns.
    #: Cursor stops at right margin.
    CUF = u"C"

    #: *Cursor back*: Move cursor left the indicated # of columns. Cursor
    #: stops at left margin.
    CUB = u"D"

    #: *Cursor next line*: Move cursor down the indicated # of lines to
    #: column 1.
    CNL = u"E"

    #: *Cursor previous line*: Move cursor up the indicated # of lines to
    #: column 1.
    CPL = u"F"

    #: *Cursor horizontal align*: Move cursor to the indicated column in
    #: current line.
    CHA = u"G"

    #: *Cursor position*: Move cursor to the indicated line, column (origin
    #: at ``1, 1``).
    CUP = u"H"

    #: *Erase data* (default: from cursor to end of line).
    ED = u"J"

    #: *Erase in line* (default: from cursor to end of line).
    EL = u"K"

    #: *Insert line*: Insert the indicated # of blank lines, starting from
    #: the current line. Lines displayed below cursor move down. Lines moved
    #: past the bottom margin are lost.
    IL = u"L"

    #: *Delete line*: Delete the indicated # of lines, starting from the
    #: current line. As lines are deleted, lines displayed below cursor
    #: move up. Lines added to bottom of screen have spaces with same
    #: character attributes as last line move up.
    DL = u"M"

    #: *Delete character*: Delete the indicated # of characters on the
    #: current line. When character is deleted, all characters to the right
    #: of cursor move left.
    DCH = u"P"

    #: *Erase character*: Erase the indicated # of characters on the
    #: current line.
    ECH = u"X"

    #: *Horizontal position relative*: Same as :data:`CUF`.
    HPR = u"a"

    #: *Vertical position adjust*: Move cursor to the indicated line,
    #: current column.
    VPA = u"d"

    #: *Vertical position relative*: Same as :data:`CUD`.
    VPR = u"e"

    #: *Horizontal / Vertical position*: Same as :data:`CUP`.
    HVP = u"f"

    #: *Tabulation clear*: Clears a horizontal tab stop at cursor position.
    TBC = u"g"

    #: *Set mode*.
    SM = u"h"

    #: *Reset mode*.
    RM = u"l"

    #: *Select graphics rendition*: The terminal can display the following
    #: character attributes that change the character display without
    #: changing the character (see :mod:`pyte.graphics`).
    SGR = u"m"

    #: *Select top and bottom margins*: Selects margins, defining the
    #: scrolling region; parameters are top and bottom line. If called
    #: without any arguments, whole screen is used.
    DECSTBM = u"r"

    #: *Horizontal position adjust*: Same as :data:`CHA`.
    HPA = u"'"


class Graphics(object):
    # -*- coding: utf-8 -*-
    """
        pyte.graphics
        ~~~~~~~~~~~~~

        This module defines graphic-related constants, mostly taken from
        :manpage:`console_codes(4)` and
        http://pueblo.sourceforge.net/doc/manual/ansi_color_codes.html.

        :copyright: (c) 2011-2013 by Selectel, see AUTHORS for details.
        :license: LGPL, see LICENSE for more details.
    """

    #: A mapping of ANSI text style codes to style names, "+" means the:
    #: attribute is set, "-" -- reset; example:
    #:
    #: >>> text[1]
    #: '+bold'
    #: >>> text[9]
    #: '+strikethrough'
    TEXT = {
        1: "+bold",
        3: "+italics",
        4: "+underscore",
        7: "+reverse",
        9: "+strikethrough",
        22: "-bold",
        23: "-italics",
        24: "-underscore",
        27: "-reverse",
        29: "-strikethrough"
    }

    #: A mapping of ANSI foreground color codes to color names, example:
    #:
    #: >>> FG[30]
    #: 'black'
    #: >>> FG[38]
    #: 'default'
    FG = {
        30: "black",
        31: "red",
        32: "green",
        33: "brown",
        34: "blue",
        35: "magenta",
        36: "cyan",
        37: "white",
        39: "default",  # white.
        50: "gray",
        51: "yellow",
        52: "smoke",
    }

    #: A mapping of ANSI background color codes to color names, example:
    #:
    #: >>> BG[40]
    #: 'black'
    #: >>> BG[48]
    #: 'default'
    BG = {
        40: "black",
        41: "red",
        42: "green",
        43: "brown",
        44: "blue",
        45: "magenta",
        46: "cyan",
        47: "white",
        49: "default",  # black.
        60: "gray",
        61: "yellow",
        62: "smoke",
    }

    # Reverse mapping of all available attributes -- keep this private!
    _SGR = {v: k for k, v in chain(FG.items(),
                                   TEXT.items())}
    _SGR.update({'bg-' + v: k for k, v in BG.items()})