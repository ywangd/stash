# -*- coding: utf-8 -*-
__version__ = '0.5.0'

__all__ = (
    'IN_PYTHONISTA', 'PYTHONISTA_VERSION', 'ON_IPAD',
    '_DEBUG_MINI_BUFFER',

    '_DEFAULT_CONFIG',
)

# Detecting environments
IN_PYTHONISTA = True
try:
    import ui
    import console
except ImportError:
    import dummyui as ui
    import dummyconsole as console
    IN_PYTHONISTA = False

PYTHONISTA_VERSION = '1.6'
try:
    from objc_util import *
except ImportError:
    from dummyobjc_util import *
    PYTHONISTA_VERSION = '1.5'

from platform import platform
if platform().find('iPad') != -1:
    ON_IPAD = True
else:
    ON_IPAD = False

# Debugging constants
_DEBUG_STREAM = 200
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
cfgfile=.stash_config
rcfile=.stashrc
historyfile=.stash_history
py_traceback=0
py_pdb=0
input_encoding_utf8=1
ipython_style_history_search=1

[display]
TEXT_FONT=('DejaVuSansMono', 12)
BUTTON_FONT=('DejaVuSansMono', 14)
BACKGROUND_COLOR=(0.0, 0.0, 0.0)
TEXT_COLOR=(1.0, 1.0, 1.0)
TINT_COLOR=(0.0, 0.0, 1.0)
INDICATOR_STYLE=white
HISTORY_MAX=30
BUFFER_MAX=300
AUTO_COMPLETION_MAX=50
VK_SYMBOLS=~/.-*|>$'=!&_"\?`
"""

