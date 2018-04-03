# coding: utf-8
"""
Launch StaSh in a more flexible and reliable way.
"""
import sys
import argparse

module_names = (
    'stash',
    'system.shcommon',
    'system.shstreams',
    'system.shscreens',
    'system.shterminal',
    'system.shui',
    'system.shio',
    'system.shiowrapper',
    'system.shparsers',
    'system.shruntime',
    'system.shthreads',
    'system.shuseractionproxy',
)

# Attempt to reload modules when startup, does not seem to work
if 'stash.stash' in sys.modules:
    for name in module_names:
        sys.modules.pop('stash.' + name)
from stash import stash

ap = argparse.ArgumentParser()
ap.add_argument('--no-cfgfile', action='store_true',
                help='do not load external config files')
ap.add_argument('--no-rcfile', action='store_true',
                help='do not load external resource file')
ap.add_argument('--no-historyfile', action='store_true',
                help='do not load history file from last session')
ap.add_argument('--log-level',
                choices=['DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL'],
                default='INFO',
                help='the logging level')
ap.add_argument('--log-file',
                help='the file to send logging messages')
ap.add_argument('--debug-switch',
                default='',
                help='a comma separate list to turn on debug switch for components')
ap.add_argument('-c', '--command',
                default=None,
                dest='command',
                help='command to run')
ap.add_argument('args',  # the editor shortcuts may pass additional arguments
                nargs='*',
                help='additional arguments (ignored)')
ns = ap.parse_args()

log_setting = {
    'level': ns.log_level,
    'file': ns.log_file,
}

if ns.debug_switch == '':
    debug = (
        # stash._DEBUG_STREAM,
        # stash._DEBUG_RENDERER,
        # stash._DEBUG_MAIN_SCREEN,
        # stash._DEBUG_MINI_BUFFER,
        # stash._DEBUG_IO,
        # stash._DEBUG_UI,
        # stash._DEBUG_TERMINAL,
        # stash._DEBUG_TV_DELEGATE,
        # stash._DEBUG_RUNTIME,
        # stash._DEBUG_PARSER,
        # stash._DEBUG_EXPANDER,
        # stash._DEBUG_COMPLETER,
    )
else:
    debug = []
    for ds in ns.debug_switch.split(','):
        ds = getattr(stash, '_DEBUG_{}'.format(ds.upper()), None)
        if ds is not None:
            debug.append(ds)

if ns.command:
    # tell StaSh not to run any command if command is passed
    # (we will call the command manually later)
    ctp = False
else:
    # tell StaSh to run the default command (totd.py)
    ctp = None


_stash = stash.StaSh(debug=debug, log_setting=log_setting,
                     no_cfgfile=ns.no_cfgfile, no_rcfile=ns.no_rcfile,
                     no_historyfile=ns.no_historyfile, command=ctp)

_stash.launch()

if ns.command:
    _stash(ns.command, add_to_history=False, persistent_level=0)