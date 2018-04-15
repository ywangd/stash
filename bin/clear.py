"""Clear the stash console output window"""
_stash = globals()['_stash']
_stash.term.truncate(size=0)
