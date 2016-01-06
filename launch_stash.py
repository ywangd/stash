# -*- coding: utf-8 -*-
"""
Launch StaSh in a way that it survives through the "globals clearing".
Globals clearing is enabled by default in Pythonista. In current v1.6
beta, it can no longer be disabled as in v1.5.
"""
import sys

if '__stash' in sys.modules:
    stash = sys.modules['__stash']
    reload(__stash)  # reload to ensure any changes to be honoured
else:
    import stash as __stash

_stash = __stash.StaSh()
_stash.run()