"""
Launch StaSh in a way that it survives through the "clearing globals".
Clearing globals is enabled by default in Pythonista. In current v1.6
beta, it can no longer be disabled as in v1.5.
"""
import stash
_stash = stash.StaSh()
_stash.run()
stash._stash=_stash

