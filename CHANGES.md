# Change Log #

### Version 0.3.0 - 2015-01-25
* New Features
    - The main `_stash` object is now callable. It is now more convenient for a
      Python script to issue Shell commands via the callable, e.g.
      `_stash('ls')`, `_stash('pwd')`
    - Sub-command auto-completion system configurable via a JSON file (currently
      supports `pip` and `git`)
    - Comments (both full line and trailing) are now allowed in shell scripts
    - All arguments are now by default converted from `unicode` type to `str`
      type with utf-8 encoding before passing them to external scripts. The
      change is to recognise that Python 2.x and its libraries are not fully
      unicode compliant. This behavior can be turned off in config file.
    - Added a config option, *py_traceback*, to display full Python exception
      trace stack for command scripts.
    - A *lib* folder is added for storing shared modules so command scripts do
      not have to include them separately.
        - These modules are stored as attributes of the main `_stash` object.

* Improvements
    - Runtime now emulates sub-shell environment even more correctly.
    - Unit tests added with Travis CI support.
    - Documentation updates

* Bug Fixes
    - Multi-statements separated by semicolon in a single line should now work
      correctly in all cases
    - White-spaces are now correctly recognized within double quotes
    - Shell scripts now correctly works with pipes
    - Various other bug fixes

* Command Scripts
    * New scripts
        - **`pip.py`** - A pare-down client for PyPI that does *search*,
          *install*, *remove*, *update*, *list*, *versions*.
            * Only works for pure Python packages that do not require
              compilation
            * No dependency handling at this stage but will report failure if
              installed package failed to import (that may be caused by
              dependency)
        - **`git.py`** - Basic git client ported from shellista
            * Requires customized
              [dulwich](https://github.com/transistor1/dulwich/archive/master.zip)
              and [gittle](https://github.com/jsbain/gittle/archive/master.zip)
              modules. 
            * If the above modules are not installed, they will be automatically
              installed the first time `git` runs. However, if they exist
              already, please make sure the above customized versions are in
              use.
        - **`scsm.py`** - StaSh Command Script Manager (initial attempt to build
          an index and a client for command scripts that perform *list*,
          *install*, *remove* and *info*)
            * It is really in a **test phase** and open to all suggestions.
            * Check out the [Index
              repo](https://github.com/ywangd/stash-command-script-index) for
              how to register new command scripts
        - **`tar.py`** - Manipulate archive files (*tar*, *gzip*, *bzip2* format)
        - **`find.py`** - Search file/directory recursively in a file hierarchy
        - **`xargs.py`** - Construct argument lists and execute
            * This command enables some quite powerful operations. A few
              examples are as follows:
                - Delete all tmp files: `find . -n "tmp*" | xargs rm`
                - Find all Python files and archive them: `find ~/Documents -n
                  "*.py" | xargs tar -zcvf scripts.tar.gz`
                - Rename all log files to log.old: `find . -n "*.log" | xargs -n
                  1 -I {} mv {} {}.log`
        - `mail.py` - Send emails with optional file attachment
        - `cut.py` - Cut out selection portions of each line of a file
        - `wc.py` - Line, word and character count
        - `md5sum.py` - Print or check MD5 checksums
        - `sha1sum.py` - Print of check SHA1 checksums
        - `sha256sum.py` - Print of check SHA256 checksums
        - `zip.py` - Package and compress files and directories
    * Changed scripts 
        - `clear.py` now replaces `cls.py` to be consisent with the Linux counterpart
        - `cat.py` - now usable on binary files 
        - `selfupdate.sh` - now removes test related files.
        - `unzip.py` - now takes a `-t` option to show file contents
        - `printenv.py` - now ignores special environment variables, e.g. `$1`


### Version 0.2.0 - 2014-12-31
* New Features
    * Added virtual keys for commonly used symbols, e.g. `~/.-*|>`
        - The keys can be customized with `VK_SYMBOLS` option in `.stash_config`
    * Shell scripts can now access arguments via special environment variables
      (`$0`, `$1`, ..., `$#`, `$@`)
    * Exit status is now available as `$?`
    * Background jobs are now allowed by appending an ampersand at the end of a
      command, e.g. `httpserver &`.
        - Background jobs are executed in Pythonista main thread and can be
          terminated by tap the close button on the interactive prompt panel.
          This enables a script to perform housekeeping tasks recieving the
          `KeyboardInterrupt` exception. An example is the `httpserver` command.
          It releases the binding port when terminated and allows subsequent
          calls to the same command without restarting Pythonista.

* Improvements
    * Parser is redesigned and optimized. It should be more efficient and
      faithful to Bash in some edge cases.
    * Runtime is optimized to make clear sub-shell emulation, especially on
      variable and environment passing between shells of different levels. 
        - Multi-line shell scripts are now executed in a single thread for
          improved efficiency
    * Auto-completion enhanced
    * Command line history management enhanced

* Command Scripts
    * New scripts 
        - **`ssh.py`** - SSH client to either execute a command or spawn an
          interactive session on remote servers.
          [pyte](https://github.com/selectel/pyte) is used for terminal
          emulation and gives the command the feel of a full-fledged SSH client. 
        - `scp.py` - Copy files from/to remote servers. 
        - `ssh-keygen.py` - Generate RSA/DSA SSH Keys.
        - `man.py` - Show help message (docstring) of a given command
        - `httpserver.py` - A simple HTTP server with **upload** function
          (ripped from https://gist.github.com/UniIsland/3346170)
        - `edit.py` - Open any text type files in Pythonista editor
        - `openin.py` - Show the **open in** dialog to open a file in external apps.
        - `quicklook.py` - iOS quick look for files of known types
        - `touch.py` - Update timestamp of the given file or create it if not exist
        - `source.py` - Evaluate a script in the current environment
        - `python.py` - run python scripts or modules
        - `which.py` - Find the exact path to a command script
        - `printhex.py` - Print hexadecimal dump of the given file 
        - `version.py` - Show StaSh installation and version information
    * Changed scripts
        - `env.py` - Replaced by `printenv.py` (`env` is now an alias to `printenv`)
        - `bh.py` - Removed. `/dev/null` is accessible in StaSh
        - `selfupdate.sh` - The GitHub branch to retrieve can now be customized
          via environment variable `SELFUPDATE_BRANCH` (default is `master`)

* Various bug fixes

### Version 0.1.0 - 2014-12-10
* initial release

