#Python 3 TODO
List of known issues, bugs and todos for stash py3 (and py2) compatibility.

#General
- 'cc'-key crashes pythonista
- more commands need to be ported
- sys.argv needs to be bytestr in py2 and unistt in py3. There is only a quick fix in place (somewhere in `shruntime.py`), which should be replaced as it only works for common usage situations
- unittests for py3
- i/o seems to switch between jobs from time to time


#`clear.py`
- prevent linebreak after screen clearing. This was removed and needs to be readded.

#`crypt.py`
- in py3, the key is shown as `b'<key>'` instead of `<key>`. Also test solution with py2

#`curl.py`
- more testing

#`easy_config.py`
- while syntax is py3 compatible, there are some errors

#Non py3-issues
- `cp.py` has no `-r` argument