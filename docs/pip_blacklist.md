#PIP blacklist
-----------------------
Starting with version 0.7.5, StaSh pip includes a blacklist.


It indicates whether a package should not be installed and what reasons
should be given.


## Motivation

The reason for this blacklist is the high number of issues regarding
installation problems of known incompatible packages. I hope that by
slowly adding packages to the blacklist we can reduce the amount of
these issues.


The blacklist was initially discussed in issue #376.


## Details
This blacklist is stored as a JSON file at `$STASH_ROOT/data/pip_blacklist.json`.
It is a dict with two top-level keys:


**`reasons`** Is a dict mapping a reasonID (str) to a message (str).
It is used to reduce redundancy of error messages.


**`blacklist`** Is a dict mapping packagename (str) to details (list).
Every package mentioned in a key of the dict is considered blacklisted.

The first (`i=0`) element of the list is the reasonID (str). Use the `reasons` toplevel
key to determine the actual reason.

The second (`i=1`) element of the list is a bool indicating whether this
blacklisting is fatal. If true, it is considered fatal. This means that
`pip` should abort the installation. Otherwise it is considered nonfatal.
This means that `pip` should skip the installation, but continue the install.
This is useful if the package can not be installed, but Pythonista already
bundles the module.

The third (`i=2`) is either `null`/`None` or a string. If it is a string
and the package is marked non-fatal, use this string as the packagename instead.
In this case, requested extras and version specifier are discarded.
