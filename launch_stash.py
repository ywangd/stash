# -*- coding: utf-8 -*-
"""
Launch StaSh in a way that it survives through the "globals clearing".
Globals clearing is enabled by default in Pythonista. In current v1.6
beta, it can no longer be disabled as in v1.5.
"""
import sys

if 'stash' in sys.modules:
    stash = sys.modules['stash']
    reload(stash)  # reload to ensure any changes to be honoured
else:
    import stash

_stash = stash.StaSh()
_stash.run()

