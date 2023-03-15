# coding: utf-8
"""
StaSh - Pythonista Shell

https://github.com/ywangd/stash
"""

__version__ = '0.8.0'

import imp as pyimp  # rename to avoid name conflict with objc_util
import logging
import logging.handlers
import os
import platform
import sys
from io import IOBase

import six
from six import BytesIO, StringIO
from six.moves.configparser import ConfigParser

# noinspection PyPep8Naming
from .system.shcommon import (_EXTERNAL_DIRS, _STASH_CONFIG_FILES, _STASH_ROOT, _SYS_STDOUT, IN_PYTHONISTA, ON_IPAD)
from .system.shcommon import Control as ctrl
from .system.shcommon import Escape as esc
from .system.shcommon import Graphics as graphics
from .system.shio import ShIO
from .system.shiowrapper import disable as disable_io_wrapper
from .system.shiowrapper import enable as enable_io_wrapper
from .system.shparsers import ShCompleter, ShExpander, ShParser
from .system.shruntime import ShRuntime
from .system.shscreens import ShSequentialScreen
from .system.shstreams import ShMiniBuffer, ShStream
from .system.shui import get_ui_implementation
from .system.shuseractionproxy import ShUserActionProxy

# Setup logging
LOGGER = logging.getLogger('StaSh')

# Debugging constants
_DEBUG_STREAM = 200
_DEBUG_RENDERER = 201
_DEBUG_MAIN_SCREEN = 202
_DEBUG_MINI_BUFFER = 203
_DEBUG_IO = 204
_DEBUG_UI = 300
_DEBUG_TERMINAL = 301
_DEBUG_TV_DELEGATE = 302
_DEBUG_RUNTIME = 400
_DEBUG_PARSER = 401
_DEBUG_EXPANDER = 402
_DEBUG_COMPLETER = 403

# Default configuration (can be overridden by external configuration file)
_DEFAULT_CONFIG = """[system]
rcfile=.stashrc
py_traceback=1
py_pdb=0
input_encoding_utf8=1
thread_type=ctypes

[display]
TEXT_FONT_SIZE={font_size}
BUTTON_FONT_SIZE=14
BACKGROUND_COLOR=(0.0, 0.0, 0.0)
TEXT_COLOR=(1.0, 1.0, 1.0)
TINT_COLOR=(0.0, 0.0, 1.0)
INDICATOR_STYLE=white
BUFFER_MAX=150
AUTO_COMPLETION_MAX=50
VK_SYMBOLS=~/.-*|>$'=!&_"\\?`

[style]
enable_styles=1
colored_errors=1

[history]
ipython_style_history_search=1
allow_double_lines=0
hide_whitespace_lines=1
maxsize=50
""".format(
    font_size=(14 if ON_IPAD else 12),
)

# create directories outside STASH_ROOT
# we should do this each time StaSh because some commands may require
# this directories
for p in _EXTERNAL_DIRS:
    if not os.path.exists(p):
        try:
            os.mkdir(p)
        except:
            pass


class StaSh(object):
    """
    Main application class. It initialize and wires the components and provide
    utility interfaces to running scripts.
    """

    PY3 = six.PY3

    def __init__(self, debug=(), log_setting=None, no_cfgfile=False, no_rcfile=False, no_historyfile=False, command=None):
        self.__version__ = __version__

        # Intercept IO
        enable_io_wrapper()

        self.config = self._load_config(no_cfgfile=no_cfgfile)
        self.logger = self._config_logging(log_setting)
        self.enable_styles = self.config.getboolean("style", "enable_styles")

        self.user_action_proxy = ShUserActionProxy(self)

        # Tab handler for running scripts
        self.external_tab_handler = None

        # Wire the components
        self.main_screen = ShSequentialScreen(
            self,
            nlines_max=self.config.getint('display',
                                          'BUFFER_MAX'),
            debug=_DEBUG_MAIN_SCREEN in debug
        )

        self.mini_buffer = ShMiniBuffer(self, self.main_screen, debug=_DEBUG_MINI_BUFFER in debug)

        self.stream = ShStream(self, self.main_screen, debug=_DEBUG_STREAM in debug)

        self.io = ShIO(self, debug=_DEBUG_IO in debug)

        ShUI, ShSequentialRenderer = get_ui_implementation()
        self.terminal = None  # will be set during UI initialisation
        self.ui = ShUI(self, debug=(_DEBUG_UI in debug), debug_terminal=(_DEBUG_TERMINAL in debug))
        self.renderer = ShSequentialRenderer(self, self.main_screen, self.terminal, debug=_DEBUG_RENDERER in debug)

        parser = ShParser(debug=_DEBUG_PARSER in debug)
        expander = ShExpander(self, debug=_DEBUG_EXPANDER in debug)
        self.runtime = ShRuntime(self, parser, expander, no_historyfile=no_historyfile, debug=_DEBUG_RUNTIME in debug)
        self.completer = ShCompleter(self, debug=_DEBUG_COMPLETER in debug)

        # Navigate to the startup folder
        if IN_PYTHONISTA:
            os.chdir(self.runtime.state.environ_get('HOME2'))
        self.runtime.load_rcfile(no_rcfile=no_rcfile)
        self.io.write(
            self.text_style(
                'StaSh v%s on python %s\n' % (
                    self.__version__,
                    platform.python_version(),
                ),
                {
                    'color': 'blue',
                    'traits': ['bold']
                },
                always=True,
            ),
        )
        # warn on py3
        if self.PY3:
            self.io.write(
                self.text_style(
                    'Warning: you are running StaSh in python3. Some commands may not work correctly in python3.\n',
                    {'color': 'red'},
                    always=True,
                ),
            )
            self.io.write(
                self.text_style(
                    'Please help us improving StaSh by reporting bugs on github.\n',
                    {
                        'color': 'yellow',
                        'traits': ['italic']
                    },
                    always=True,
                ),
            )
        # Load shared libraries
        self._load_lib()

        # run command (this calls script_will_end)
        if command is None:
            # show tip of the day
            command = '$STASH_ROOT/bin/totd.py'
        if command:
            # do not run command if command is False (but not None)
            if self.runtime.debug:
                self.logger.debug("Running command: {!r}".format(command))
            self(command, add_to_history=False, persistent_level=0)

    def __call__(self, input_, persistent_level=2, *args, **kwargs):
        """ This function is to be called by external script for
         executing shell commands """
        worker = self.runtime.run(input_, persistent_level=persistent_level, *args, **kwargs)
        worker.join()
        return worker

    @staticmethod
    def _load_config(no_cfgfile=False):
        config = ConfigParser()
        config.optionxform = str  # make it preserve case

        # defaults
        if not six.PY3:
            config.readfp(BytesIO(_DEFAULT_CONFIG))
        else:
            config.read_file(StringIO(_DEFAULT_CONFIG))

        # update from config file
        if not no_cfgfile:
            config.read(os.path.join(_STASH_ROOT, f) for f in _STASH_CONFIG_FILES)

        return config

    @staticmethod
    def _config_logging(log_setting):

        logger = logging.getLogger('StaSh')

        _log_setting = {
            'level': 'DEBUG',
            'stdout': True,
        }

        _log_setting.update(log_setting or {})

        level = {
            'CRITICAL': logging.CRITICAL,
            'ERROR': logging.ERROR,
            'WARNING': logging.WARNING,
            'INFO': logging.INFO,
            'DEBUG': logging.DEBUG,
            'NOTSET': logging.NOTSET,
        }.get(_log_setting['level'],
              logging.DEBUG)

        logger.setLevel(level)

        if not logger.handlers:
            if _log_setting['stdout']:
                _log_handler = logging.StreamHandler(_SYS_STDOUT)
            else:
                _log_handler = logging.handlers.RotatingFileHandler('stash.log', mode='w')
            _log_handler.setLevel(level)
            _log_handler.setFormatter(
                logging.Formatter(
                    '[%(asctime)s] [%(levelname)s] [%(threadName)s] [%(name)s] [%(funcName)s] [%(lineno)d] - %(message)s'
                )
            )
            logger.addHandler(_log_handler)

        return logger

    def _load_lib(self):
        """
        Load library files as modules and save each of them as attributes
        """
        lib_path = os.path.join(_STASH_ROOT, 'lib')
        os.environ['STASH_ROOT'] = _STASH_ROOT  # libcompleter needs this value
        try:
            for f in os.listdir(lib_path):
                fp = os.path.join(lib_path, f)
                if f.startswith('lib') and f.endswith('.py') and os.path.isfile(fp):
                    name, _ = os.path.splitext(f)
                    if self.runtime.debug:
                        self.logger.debug("Attempting to load library '{}'...".format(name))
                    try:
                        self.__dict__[name] = pyimp.load_source(name, fp)
                    except Exception as e:
                        self.write_message('%s: failed to load library file (%s)' % (f, repr(e)), error=True)
        finally:  # do not modify environ permanently
            os.environ.pop('STASH_ROOT')

    def write_message(self, s, error=False, prefix="stash: "):
        """
        Write a message to the output.
        :param s: message to write
        :type w: str
        :param error: whether this is an error message
        :type error: bool
        """
        s = '%s%s\n' % (prefix, s)
        if error:
            if self.runtime.debug:
                self.logger.error(s)
            if self.runtime.colored_errors:
                s = self.text_color(s, "red")
        else:
            if self.runtime.debug:
                self.logger.info(s)
        self.io.write(s)

    def launch(self, command=None):
        """
        Launch StaSh, presenting the UI.
        """
        self.ui.show()
        # self.terminal.set_focus()
    
    def close(self):
        """
        Quit StaSh.
        StaSh is based arround the UI, so we delegate this task to the UI,
        which in turn will call self.on_exit().
        """
        self.ui.close()
    
    def on_exit(self):
        """
        This method will be called when StaSh is about the be closed.
        """
        self.runtime.save_history()
        self.cleanup()
        # Clear the stack or the stdout becomes unusable for interactive prompt
        self.runtime.worker_registry.purge()
        

    def cleanup(self):
        """
        Perform cleanup here.
        """
        disable_io_wrapper()

    def get_workers(self):
        """
        Return a list of all workers..
        :return: a list of all workers
        :rtype: list of [stash.system.shtreads.BaseThread]
        """
        return [worker for worker in self.runtime.worker_registry]

    # noinspection PyProtectedMember
    # @staticmethod
    def text_style(self, s, style, always=False):
        """
        Style the given string with ASCII escapes.

        :param str s: String to decorate
        :param dict style: A dictionary of styles
        :param bool always: If true, style will be applied even for pipes.
        :return:
        """
        # No color for pipes, files and Pythonista console
        if not self.enable_styles or (not always and (isinstance(sys.stdout,
                                                                 (StringIO,
                                                                  IOBase))  # or sys.stdout.write.im_self is _SYS_STDOUT
                                                      or sys.stdout is _SYS_STDOUT)):
            return s

        fmt_string = u'%s%%d%s%%s%s%%d%s' % (ctrl.CSI, esc.SGR, ctrl.CSI, esc.SGR)
        for style_name, style_value in style.items():
            if style_name == 'color':
                color_id = graphics._SGR.get(style_value.lower())
                if color_id is not None:
                    s = fmt_string % (color_id, s, graphics._SGR['default'])
            elif style_name == 'bgcolor':
                color_id = graphics._SGR.get('bg-' + style_value.lower())
                if color_id is not None:
                    s = fmt_string % (color_id, s, graphics._SGR['default'])
            elif style_name == 'traits':
                for val in style_value:
                    val = val.lower()
                    if val == 'bold':
                        s = fmt_string % (graphics._SGR['+bold'], s, graphics._SGR['-bold'])
                    elif val == 'italic':
                        s = fmt_string % (graphics._SGR['+italics'], s, graphics._SGR['-italics'])
                    elif val == 'underline':
                        s = fmt_string % (graphics._SGR['+underscore'], s, graphics._SGR['-underscore'])
                    elif val == 'strikethrough':
                        s = fmt_string % (graphics._SGR['+strikethrough'], s, graphics._SGR['-strikethrough'])

        return s

    def text_color(self, s, color_name='default', **kwargs):
        return self.text_style(s, {'color': color_name}, **kwargs)

    def text_bgcolor(self, s, color_name='default', **kwargs):
        return self.text_style(s, {'bgcolor': color_name}, **kwargs)

    def text_bold(self, s, **kwargs):
        return self.text_style(s, {'traits': ['bold']}, **kwargs)

    def text_italic(self, s, **kwargs):
        return self.text_style(s, {'traits': ['italic']}, **kwargs)

    def text_bold_italic(self, s, **kwargs):
        return self.text_style(s, {'traits': ['bold', 'italic']}, **kwargs)

    def text_underline(self, s, **kwargs):
        return self.text_style(s, {'traits': ['underline']}, **kwargs)

    def text_strikethrough(self, s, **kwargs):
        return self.text_style(s, {'traits': ['strikethrough']}, **kwargs)
