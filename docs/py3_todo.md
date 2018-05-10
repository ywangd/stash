#Python 3 TODO
List of known issues, bugs and todos for stash py3 (and py2) compatibility.

#General
- ctype threads in py3 bugged (crash on cc and kill)
- more commands need to be ported
- sys.argv needs to be bytestr in py2 and unistt in py3. There is only a quick fix in place (somewhere in `shruntime.py`), which should be replaced as it only works for common usage situations
- i/o seems to switch between jobs from time to time


#`crypt.py`
- in py3, the key is shown as `b'<key>'` instead of `<key>`. Also test solution with py2

#`curl.py`
- more testing

#`pip.py`
- many bugs
- installation using `setupy.py` fails most of the time, always falls back to package detection
- maybe `pip3` for py3 instead of a single `pip` command.

#Non py3-issues
- `cp.py` has no `-r` argument
